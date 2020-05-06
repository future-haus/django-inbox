from django.http import HttpResponse

from inbox.utils import process_new_messages, process_new_message_logs


def view_process_new_messages(request):

    process_new_messages()

    return HttpResponse(status=200)


def view_process_new_message_logs(request):

    process_new_message_logs()

    return HttpResponse(status=200)
