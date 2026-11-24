from datetime import timedelta
from secrets import token_urlsafe

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm, UsernameField
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .models import PasswordResetRequest, User


LINK_LIFETIME = timedelta(hours=24)
ATTEMPT_WINDOW = 600
SESSION_TOKEN = 'participant_password_reset'
ELIGIBLE = {'is_active': True, 'is_staff': False, 'is_superuser': False}


class RequestForm(forms.Form):
    username = UsernameField(
        label='Nickname',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autocapitalize': 'none', 'autofocus': True}),
    )


def eligible_users():
    return User.objects.filter(**ELIGIBLE).exclude(role=User.Role.COUPLE)


def within_limit(key, limit):
    cache.add(key, 0, ATTEMPT_WINDOW)
    try:
        return cache.incr(key) <= limit
    except ValueError:
        return False


def allow_attempt(request):
    # A reverse proxy may share one address among many browsers. Do not trust
    # client-supplied forwarding headers; use a higher ceiling for that address.
    address = request.META.get('REMOTE_ADDR', 'unknown')
    if not within_limit(f'password-reset:address:{address}', 120):
        return False
    browser = request.session.get('password_reset_browser')
    if not browser:
        browser = request.session['password_reset_browser'] = token_urlsafe(16)
    return within_limit(f'password-reset:browser:{browser}', 5)


def digest(user, token):
    return salted_hmac('wedding.participant.password-reset', f'{user.pk}:{user.password}:{token}', algorithm='sha256').hexdigest()


def valid_link(user, reset, token):
    return (
        reset is not None and reset.issued_at is not None
        and timezone.now() < reset.issued_at + LINK_LIFETIME
        and constant_time_compare(reset.token_digest, digest(user, token))
    )


def invalid_link(request):
    return render(request, 'wedding/page.html', {
        'title': 'Redefinir senha',
        'message': 'Link inválido ou expirado. Solicite um novo link aos noivos.',
    }, status=400)


@never_cache
@require_http_methods(['GET', 'HEAD', 'POST'])
def request_reset(request):
    form = RequestForm(request.POST if request.method == 'POST' else None)
    context = {'title': 'Esqueci minha senha', 'form': form}
    if request.method == 'POST':
        if not allow_attempt(request):
            context['message'] = 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
            return render(request, 'wedding/page.html', context, status=429)
        if form.is_valid():
            with transaction.atomic():
                user = eligible_users().select_for_update().filter(username=form.cleaned_data['username']).first()
                if user is not None:
                    PasswordResetRequest.objects.get_or_create(user=user)
                    return redirect('password_reset_requested')
            form.add_error('username', 'Usuário não encontrado ou ainda não ativado.')
    return render(request, 'wedding/page.html', context)


@require_safe
def requested(request):
    return render(request, 'wedding/page.html', {
        'title': 'Pedido enviado',
        'message': 'Seu pedido foi enviado aos noivos. Eles vão confirmar sua identidade antes de enviar o link.',
    })


def require_couple(request):
    if not request.user.is_active or request.user.role != User.Role.COUPLE:
        raise PermissionDenied


def render_panel(request, reset_link=None, recipient=None):
    resets = PasswordResetRequest.objects.filter(user__in=eligible_users()).select_related('user').order_by('requested_at')
    return render(request, 'wedding/password_resets.html', {
        'resets': resets,
        'reset_link': reset_link,
        'recipient': recipient,
        'pending_resets_count': resets.count(),
    })


@never_cache
@login_required
@require_safe
def panel(request):
    require_couple(request)
    return render_panel(request)


@never_cache
@login_required
@require_POST
def issue_link(request, pk):
    require_couple(request)
    with transaction.atomic():
        user = get_object_or_404(eligible_users().select_for_update(), pk=pk)
        reset = get_object_or_404(PasswordResetRequest, user=user)
        token = token_urlsafe(32)
        reset.token_digest = digest(user, token)
        reset.issued_at = timezone.now()
        reset.save(update_fields=['token_digest', 'issued_at'])
    path = reverse('password_reset_link', kwargs={'pk': pk, 'token': token})
    return render_panel(request, reset_link=request.build_absolute_uri(path), recipient=user)


@never_cache
@require_safe
def open_link(request, pk, token):
    user = eligible_users().filter(pk=pk).first()
    reset = PasswordResetRequest.objects.filter(user_id=pk).first() if user else None
    if not valid_link(user, reset, token):
        response = invalid_link(request)
    else:
        request.session.cycle_key()
        request.session[SESSION_TOKEN] = [pk, token]
        response = redirect('password_reset_confirm', pk=pk)
    response['Referrer-Policy'] = 'no-referrer'
    return response


@never_cache
@require_http_methods(['GET', 'HEAD', 'POST'])
def confirm(request, pk):
    credentials = request.session.get(SESSION_TOKEN)
    if not credentials or credentials[0] != pk:
        return invalid_link(request)
    token = credentials[1]
    with transaction.atomic():
        users = eligible_users()
        if request.method == 'POST':
            users = users.select_for_update()
        user = users.filter(pk=pk).first()
        reset = PasswordResetRequest.objects.filter(user_id=pk).first() if user else None
        if not valid_link(user, reset, token):
            request.session.pop(SESSION_TOKEN, None)
            return invalid_link(request)
        form = SetPasswordForm(user, request.POST if request.method == 'POST' else None)
        if request.method == 'POST' and form.is_valid():
            form.save()
            reset.delete()
            request.session.pop(SESSION_TOKEN, None)
            return redirect('login')
    response = render(request, 'wedding/page.html', {'title': 'Redefinir senha', 'form': form})
    response['Referrer-Policy'] = 'same-origin'
    return response
