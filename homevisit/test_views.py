import logging

from django.test import TestCase
from django.urls import reverse

from .models import Household, Person, Meeting
from .forms import HouseholdForm, OwnerForm
from .test_models import RecurringMeetingTestConfig, populate_example_meetings

logger = logging.getLogger(__name__)


class IndexViewTests(TestCase):
    def setUp(self):
        self.meeting_config = RecurringMeetingTestConfig()
        populate_example_meetings(self.meeting_config)

    def test_index_view(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(200, response.status_code)
        self.assertIn(
            "homevisit/index.html", [template.name for template in response.templates]
        )

        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], HouseholdForm)
        self.assertIn("owner_form", response.context)
        self.assertIsInstance(response.context["owner_form"], OwnerForm)

    def test_index_post(self):
        first_name = "TestFirst"
        last_name = "TestLast"
        address = "Test Address"
        meeting_choice = Meeting.objects.all()[0]
        data = {
            "ownerForm-first_name": first_name,
            "ownerForm-last_name": last_name,
            "ownerForm-phone_number": "5307777777",
            "ownerForm-email": "user@test.com",
            "address": address,
            "meeting": meeting_choice.id,
        }
        response = self.client.post(reverse("index"), data, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, reverse("success"))

        self.assertEqual(1, Household.objects.count())
        house = Household.objects.all().get()
        self.assertEqual(address, house.address)

        self.assertEqual(1, house.person_set.count())
        person = house.person_set.all().get()
        self.assertEqual(first_name, person.first_name)
        self.assertEqual(last_name, person.last_name)

        self.assertEqual(1, house.meeting_set.count())
        meeting = house.meeting_set.all().get()
        self.assertEqual(meeting_choice, meeting)

        # When the next person comes to the site...
        response = self.client.get(reverse("index"))
        self.assertEqual(200, response.status_code)

        # ... there should be one-less Meeting choice to select from
        choices = [
            choice for choice in response.context["form"].fields["meeting"].choices
        ]
        self.assertEqual(Meeting.objects.count() - 1, len(choices))

        # ... and the meeting_choice.id we just reserved shouldn't be an option
        meeting_choice_ids = [_id for (_id, _) in choices]
        self.assertNotIn(meeting_choice.id, meeting_choice_ids)

    def test_index_post_try_to_reserve_same_meeting(self):
        # User1 and User2 will attempt to reserve this same meeting instance
        meeting_choice = Meeting.objects.all()[0]

        # To begin with, this meeting choice is available for both users
        response = self.client.get(reverse("index"))
        self.assertEqual(200, response.status_code)
        choices = [
            choice for choice in response.context["form"].fields["meeting"].choices
        ]
        meeting_choice_ids = [_id for (_id, _) in choices]
        self.assertIn(meeting_choice.id, meeting_choice_ids)

        # Both users fill out the form, attempting to reserve the same meeting_choice
        user1_first_name = "User1"
        user1_address = "User 1 Address"
        user1_data = {
            "ownerForm-first_name": user1_first_name,
            "ownerForm-email": "user1@test.com",
            "ownerForm-phone_number": "",
            "address": user1_address,
            "meeting": meeting_choice.id,
        }

        user2_first_name = "User2"
        user2_address = "User 2 Address"
        user2_data = {
            "ownerForm-first_name": user2_first_name,
            "ownerForm-email": "user2@test.com",
            "ownerForm-phone_number": "",
            "address": user2_address,
            "meeting": meeting_choice.id,
        }

        # User 1: submits first (and is successful). NOTE: The view's POST is atomic.
        response = self.client.post(reverse("index"), user1_data, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, reverse("success"))
        self.assertIn(
            "homevisit/success.html", [template.name for template in response.templates]
        )

        # User 2: submits after.
        response = self.client.post(reverse("index"), user2_data, follow=True)
        self.assertEqual(200, response.status_code)

        # User 2: No redirects; lands back on index
        self.assertFalse(response.redirect_chain)
        self.assertIn(
            "homevisit/index.html", [template.name for template in response.templates]
        )

        # User 2: Household form not valid; mentions that meeting not currently available
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(1, len(form.errors))
        self.assertIn("meeting is not currently available", form.errors["meeting"][0])

        # Verify User 1 saved and reserved
        self.assertEqual(1, Person.objects.filter(first_name=user1_first_name).count())
        self.assertEqual(1, Household.objects.filter(address=user1_address).count())
        user1 = Person.objects.get(first_name=user1_first_name)
        self.assertIsNotNone(user1.household)
        self.assertEqual(1, user1.household.meeting_set.count())
        self.assertEqual(meeting_choice, user1.household.meeting_set.get())

        # Verify User 2' data is not saved
        self.assertEqual(0, Person.objects.filter(first_name=user2_first_name).count())
        self.assertEqual(0, Household.objects.filter(address=user2_address).count())
