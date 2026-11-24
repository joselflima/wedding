from urllib.parse import urlencode

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.views.decorators.http import require_http_methods, require_safe
from .models import PasswordResetRequest, User
from .password_reset import eligible_users


def _participants_queryset():
    return User.objects.filter(is_staff=False, is_superuser=False).exclude(role=User.Role.COUPLE)


def _pending_resets_count():
    return PasswordResetRequest.objects.filter(user__in=eligible_users()).count()


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('name','username','phone','role')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [(k,v) for k,v in User.Role.choices if k != 'couple']
    def clean_role(self):
        role = self.cleaned_data['role']
        if role == 'couple':
            raise forms.ValidationError('Tipo indisponível.')
        return role

def home(request):
    context = {}
    if request.user.is_authenticated and request.user.role == User.Role.COUPLE:
        participants = _participants_queryset()
        total = participants.count()
        active = participants.filter(is_active=True).count()
        context['dashboard'] = {
            'total_participants': total,
            'active_participants': active,
            'pending_participants': total - active,
            'pending_password_resets': _pending_resets_count(),
        }
    return render(request, 'wedding/home.html', context)


@require_safe
def manifest(request):
    return JsonResponse({
        'id': '/',
        'name': 'Maria Eduarda e José Lucas',
        'short_name': 'M&J',
        'lang': 'pt-BR',
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'theme_color': '#59633a',
        'background_color': '#f3e7d3',
        'icons': [
            {'src': static(f'wedding/icon-{size}.png'), 'sizes': f'{size}x{size}', 'type': 'image/png'}
            for size in (192, 512)
        ],
    }, content_type='application/manifest+json')


@login_required
def people(request, pk=None):
    if request.user.role != 'couple':
        raise PermissionDenied
    person = get_object_or_404(User, pk=pk) if pk else None
    if person and (person.role == 'couple' or person.is_staff or person.is_superuser):
        raise PermissionDenied
    link = None
    if request.method == 'POST' and person and request.POST.get('action') == 'delete':
        person.delete()
        return redirect('people')
    if request.method == 'POST' and person and request.POST.get('action') == 'link':
        person.set_unusable_password()
        person.is_active = False
        person.save()
        link = request.build_absolute_uri(f'/activate/{person.pk}/{default_token_generator.make_token(person)}/')
        form = ParticipantForm(instance=person)
    else:
        form = ParticipantForm(request.POST or None, instance=person)
        if request.method == 'POST' and form.is_valid():
            obj = form.save(commit=False)
            if not person:
                obj.is_active = False
                obj.set_unusable_password()
            obj.save()
            return redirect('person', pk=obj.pk)
    base_rows = _participants_queryset().order_by('name')
    total_count = base_rows.count()
    active_count = base_rows.filter(is_active=True).count()
    pending_count = total_count - active_count

    rows = base_rows
    q = request.GET.get('q', '').strip()
    if q:
        rows = rows.filter(Q(name__icontains=q) | Q(username__icontains=q))
    selected_role = request.GET.get('role', '')
    if selected_role:
        rows = rows.filter(role=selected_role)
    selected_status = request.GET.get('status', '')
    if selected_status == 'active':
        rows = rows.filter(is_active=True)
    elif selected_status == 'pending':
        rows = rows.filter(is_active=False)
    else:
        selected_status = ''

    paginator = Paginator(rows, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = {}
    if q:
        query_params['q'] = q
    if selected_role:
        query_params['role'] = selected_role
    if selected_status:
        query_params['status'] = selected_status

    filter_roles = [(k, v) for k, v in User.Role.choices if k != User.Role.COUPLE]
    return render(request, 'wedding/people.html', {
        'create_form': ParticipantForm(auto_id='create_%s') if person else form,
        'form': form,
        'rows': page_obj,
        'page_obj': page_obj,
        'person': person,
        'link': link,
        'roles': filter_roles,
        'total_count': total_count,
        'active_count': active_count,
        'pending_count': pending_count,
        'filtered_count': paginator.count,
        'has_filters': bool(q or selected_role or selected_status),
        'selected_status': selected_status,
        'selected_role': selected_role,
        'search_query': q,
        'pagination_query': urlencode(query_params),
        'pending_resets_count': _pending_resets_count(),
    })

@require_http_methods(['GET', 'HEAD', 'POST'])
def activate(request, pk, token):
    submitted = request.method == 'POST'
    with transaction.atomic():
        users = User.objects.filter(is_active=False, is_staff=False, is_superuser=False)
        if submitted:
            users = users.select_for_update()
        person = users.filter(pk=pk).first()
        if person is None or not default_token_generator.check_token(person, token):
            response = render(request, 'wedding/page.html', {
                'title': 'Convite indisponível',
                'message': 'Este link não está mais disponível. Se você já definiu a senha, entre pelo login. Caso contrário, peça um novo convite aos noivos.',
            }, status=400)
        else:
            form = SetPasswordForm(person, request.POST if submitted else None)
            if submitted and form.is_valid():
                form.save(commit=False)
                person.is_active = True
                person.save(update_fields=['password', 'is_active'])
                response = redirect('login')
            else:
                response = render(request, 'wedding/page.html', {'form': form})
    # The form needs a same-origin Referer for HTTPS CSRF checks.
    response['Referrer-Policy'] = 'same-origin' if response.status_code == 200 else 'no-referrer'
    response['Cache-Control'] = 'no-store'
    return response
