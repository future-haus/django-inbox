from django.http import HttpResponse

from inbox.utils import process_new_messages


def view_process_new_messages(request):

    process_new_messages()

    return HttpResponse(status=200)
