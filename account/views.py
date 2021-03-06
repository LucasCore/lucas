from django.views.generic import ListView, RedirectView
from django.views.generic.edit import FormView, UpdateView, DeletionMixin, CreateView
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.mail import send_mail
from account.models import User, Expert
from account.forms import LoginForm, ExpertForm, ModeratorForm, PasswordChangeForm, ForgotPasswordForm


class SendEmailMixin:
    email_template_name = ''  # path to template for email message
    email_subject = ''
    email_context_data = {}
    from_email = 'admin@lucas.com'
    receivers = tuple()

    def get_email_context_data(self):
        return self.email_context_data

    def get_receivers(self):
        return self.receivers

    def render_email(self):
        return render_to_string(self.email_template_name, self.get_email_context_data())

    def send(self):
        send_mail(self.email_subject, self.render_email(), self.from_email, self.get_receivers(), fail_silently=False)


class IndexView(RedirectView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(reverse_lazy('account:cabinet'))
        else:
            return HttpResponseRedirect(reverse_lazy('account:login'))


class LoginView(FormView):
    form_class = LoginForm
    template_name = 'account/login.html'
    success_url = reverse_lazy("account:cabinet")

    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())

        return HttpResponseRedirect(self.success_url)


class ForgotPasswordView(FormView, SendEmailMixin):
    form_class = ForgotPasswordForm
    template_name = 'account/forgot_password.html'
    success_url = reverse_lazy('account:login')

    email_template_name = 'account/email/new_password.html'
    email_subject = 'Пароль обновлен'

    object = None
    password = None

    def form_valid(self, form):
        self.object = form.get_user()
        self.password = User.objects.make_random_password(length=4)
        self.object.set_password(self.password)
        self.object.save()

        messages.success(self.request, 'пароль обновлен')
        self.send()

        return HttpResponseRedirect(self.success_url)

    def get_receivers(self):
        return self.object.email,

    def get_email_context_data(self):
        return {'user': self.object, 'password': self.password}


class ShowProfileView(LoginRequiredMixin, FormView):
    model = User
    success_url = reverse_lazy("account:cabinet")
    template_name = 'account/profile/show_profile.html'

    def get_form(self, form_class=None):
        if self.get_object().is_admin:
            form = ModeratorForm
        else:
            form = ExpertForm
        return form(**self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super(ShowProfileView, self).get_context_data(**kwargs)
        context['password_change_form'] = PasswordChangeForm()
        return context

    def get_initial(self):
        return self.model.objects.filter(email=self.get_object().email).values()[0]

    def get_object(self):
        return self.request.user

    def form_valid(self, form=None):
        profile = User.objects.filter(email=self.get_object().email)
        profile.update(**form.cleaned_data)
        messages.success(self.request, 'Информация изменена')
        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form=None):
        messages.error(self.request, 'Форма невалидна')
        return render(self.request, self.template_name, {"form": form})


class ChangePasswordView(LoginRequiredMixin, FormView):
    http_method_names = ['post']
    form_class = PasswordChangeForm
    success_url = reverse_lazy('account:cabinet')

    def form_valid(self, form):
        user = self.get_object()

        logout(self.request)

        user.set_password(form.cleaned_data['new_password'])
        user.save()

        user = authenticate(email=user.email, password=form.cleaned_data['new_password'])
        login(self.request, user)

        messages.success(self.request, 'Пароль успешно изменён')
        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form):
        print(form)
        messages.error(self.request, 'Некорректно заполненая форма')
        return HttpResponseRedirect(self.success_url)

    def get_object(self):
        return self.request.user


class ExpertList(PermissionRequiredMixin, ListView):
    queryset = Expert.objects.filter(is_expert=True)
    template_name = "account/expert/index.html"

    permission_required = ('manipulate_expert',)


class CreateExpertView(SendEmailMixin, CreateView):
    model = Expert
    form_class = ExpertForm
    object = None
    password = None
    template_name = 'account/expert/new.html'
    success_url = reverse_lazy('account:experts')

    permission_required = ('manipulate_expert',)

    email_subject = 'Добро пожаловать'
    email_template_name = 'account/email/invite_expert.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.password = User.objects.make_random_password(length=4)
        self.object.set_password(self.password)
        self.object.save()

        messages.success(self.request, "Пользователь добавлен")
        self.send()
        return HttpResponseRedirect(self.success_url)

    def get_email_context_data(self):
        return {'user': self.object, 'password': self.password}

    def get_receivers(self):
        return self.object.email,


class ExpertView(DeletionMixin, UpdateView):
    model = Expert
    form_class = ExpertForm
    template_name = 'account/expert/edit.html'
    success_url = reverse_lazy('account:experts')

    permission_required = ('manipulate_expert',)


class ToggleActivityExpertView(UpdateView):
    http_method_names = ['get']
    model = Expert
    success_url = reverse_lazy('account:experts')

    permission_required = ('manipulate_expert',)

    def get(self, request, *args, **kwargs):
        if self.object.is_active:
            self.object.is_active = False
            messages.success(self.request, "Пользователь заморожен")
        else:
            self.object.is_active = True
            messages.success(self.request, "Пользователь разморожен")
        self.object.save()
        HttpResponseRedirect(self.success_url)


class ResetPasswordView(SendEmailMixin, UpdateView):
    http_method_names = ['get']
    model = Expert
    success_url = reverse_lazy('account:experts')

    permission_required = ('manipulate_expert',)

    email_template_name = 'account/email/new_password.html'
    email_subject = 'Пароль обновлен'
    from_email = 'admin@lucas.com'

    password = None

    def get(self, request, *args, **kwargs):
        self.password = User.objects.make_random_password(length=4)
        expert = self.get_object()
        expert.set_password(self.password)
        expert.save()

        self.send()
        return HttpResponseRedirect(self.success_url)

    def get_email_context_data(self):
        return {'user': self.get_object(), 'password': self.password}

    def get_receivers(self):
        return self.get_object().email,
