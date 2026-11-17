from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .models import User

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
    return render(request, 'wedding/home.html')

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
    rows = User.objects.filter(is_staff=False, is_superuser=False).exclude(role='couple').order_by('name')
    q = request.GET.get('q', '')
    rows = rows.filter(Q(name__icontains=q) | Q(username__icontains=q))
    if request.GET.get('role'):
        rows = rows.filter(role=request.GET['role'])
    return render(request, 'wedding/people.html', {'create_form': ParticipantForm(auto_id='create_%s') if person else form, 'form':form,'rows':rows,'person':person,'link':link,'roles':User.Role.choices})

def activate(request, pk, token):
    person = get_object_or_404(User, pk=pk, is_active=False, is_staff=False, is_superuser=False)
    if not default_token_generator.check_token(person, token):
        return render(request, 'wedding/page.html', {'message':'Link inválido ou expirado.'}, status=400)
    form = SetPasswordForm(person, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        person.is_active = True
        person.save()
        return redirect('login')
    response = render(request, 'wedding/page.html', {'form':form})
    # Preserve same-origin Referer for HTTPS CSRF checks without leaking invitation tokens.
    response['Referrer-Policy'] = 'same-origin'
    response['Cache-Control'] = 'no-store'
    return response
