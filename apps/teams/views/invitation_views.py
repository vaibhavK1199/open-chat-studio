import uuid

from allauth.account.views import SignupView
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ..invitations import clear_invite_from_session, process_invitation
from ..models import Invitation
from ..roles import is_member


def accept_invitation(request, invitation_id: uuid.UUID):
    invitation = get_object_or_404(Invitation, id=invitation_id)
    if not invitation.is_accepted:
        # set invitation in the session in case needed later - e.g. to redirect after login
        request.session["invitation_id"] = str(invitation_id)
    else:
        clear_invite_from_session(request)
    if (
        request.user.is_authenticated
        and request.user.email.lower() == invitation.email.lower()
        and is_member(request.user, invitation.team)
    ):
        messages.info(
            request,
            _("It looks like you're already a member of {team}. You've been redirected.").format(
                team=invitation.team.name
            ),
        )
        return HttpResponseRedirect(reverse("web_team:home", args=[invitation.team.slug]))

    if request.method == "POST":
        # accept invitation workflow
        if not request.user.is_authenticated:
            messages.error(request, _("Please log in again to accept your invitation."))
            return HttpResponseRedirect(reverse(settings.LOGIN_URL))
        else:
            if invitation.is_accepted:
                messages.error(request, _("Sorry, it looks like that invitation link has expired."))
                return HttpResponseRedirect(reverse("web:home"))
            else:
                process_invitation(invitation, request.user)
                clear_invite_from_session(request)
                messages.success(request, _("You successfully joined {}").format(invitation.team.name))
                return HttpResponseRedirect(reverse("web_team:home", args=[invitation.team.slug]))

    return render(
        request,
        "teams/accept_invite.html",
        {
            "invitation": invitation,
            "invitation_url": reverse("teams:accept_invitation", args=[invitation_id]),
        },
    )


class SignupAfterInvite(SignupView):
    def get(self, request, *args, **kwargs):
        if self.invitation.is_accepted:
            messages.warning(
                self.request,
                _("The invitation has already been accepted. Please sign in to continue or request a new invitation."),
            )
            return redirect("web:home")
        return super().get(request, *args, **kwargs)

    def is_open(self):
        """Allow signups from invitations even if public signups are closed."""
        return True

    @property
    def invitation(self) -> Invitation:
        from ..models import Invitation

        invitation_id = self.kwargs["invitation_id"]
        return get_object_or_404(Invitation, id=invitation_id)

    def get_initial(self):
        initial = super().get_initial()
        if self.invitation:
            initial["team_name"] = self.invitation.team.name
            initial["email"] = self.invitation.email
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.invitation:
            context["invitation"] = self.invitation
        return context
