from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render

from apps.teams.models import Membership
from apps.teams.superuser_utils import apply_temporary_superuser_access


class ConfirmIdentityForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)


@user_passes_test(lambda u: u.is_superuser)
def acquire_superuser_powers(request, team_slug):
    if not request.team:
        raise Http404

    if request.method == "POST":
        form = ConfirmIdentityForm(request.POST)
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data["password"]):
                form.add_error("password", "Invalid password")
            else:
                apply_temporary_superuser_access(request, team_slug)
                redirect_to = form.cleaned_data["redirect"] or "/"
                return HttpResponseRedirect(redirect_to or "/")
    else:
        redirect_to = request.GET.get("next", "")
        if Membership.objects.filter(team=request.team, user=request.user).exists():
            return HttpResponseRedirect(redirect_to or "/")

        form = ConfirmIdentityForm(initial={"redirect": redirect_to})

    return render(
        request,
        "teams/temporary_superuser_powers.html",
        {
            "team": request.team,
            "form": form,
        },
    )


@user_passes_test(lambda u: u.is_superuser)
def release_superuser_powers(request):
    # team = get_object_or_404(Team, slug=team_slug)
    return render(
        request,
        "teams/temporary_superuser_powers.html",
        {},
    )
