from django.core.management.base import BaseCommand, CommandError
from django.template import loader, TemplateDoesNotExist

from beautifultable import BeautifulTable
from inbox import settings as inbox_settings
from inbox.constants import MessageMedium
from inbox.models import MessageLog


class Command(BaseCommand):
    help = 'Use inbox config and determine if necessary templates are available.'

    # def add_arguments(self, parser):
    #     parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):

        message_groups = []
        for message_group in inbox_settings.get_config()['MESSAGE_GROUPS']:
            for k, v in message_group['preference_defaults'].items():
                if v is not None:
                    template_names = MessageLog._get_subject_template_names(message_group['id'], MessageMedium.get(k.upper()))
                    template_names.extend(MessageLog._get_body_template_names(message_group['id'], MessageMedium.get(k.upper())))
                    # TODO Add base template to template names

                    for template_name in template_names:
                        try:
                            loader.get_template(template_name)
                        except TemplateDoesNotExist:
                            if MessageMedium.get(k.upper()) == MessageMedium.APP_PUSH:
                                message_groups.append({
                                    'file': template_name,
                                    'key': message_group['id'],
                                    'medium': k.lower(),
                                    'required': False,
                                    'found': False
                                })
                            if MessageMedium.get(k.upper()) == MessageMedium.EMAIL:
                                message_groups.append({
                                    'file': template_name,
                                    'key': message_group['id'],
                                    'medium': k.lower(),
                                    'required': True,
                                    'found': False
                                })
                        else:
                            if MessageMedium.get(k.upper()) == MessageMedium.APP_PUSH:
                                message_groups.append({
                                    'file': template_name,
                                    'key': message_group['id'],
                                    'medium': k.lower(),
                                    'required': False,
                                    'found': True
                                })
                            if MessageMedium.get(k.upper()) == MessageMedium.EMAIL:
                                message_groups.append({
                                    'file': template_name,
                                    'key': message_group['id'],
                                    'medium': k.lower(),
                                    'required': True,
                                    'found': True
                                })

        table = BeautifulTable()
        table.column_headers = ['File', 'Required', 'Found']
        table.column_alignments['File'] = BeautifulTable.ALIGN_LEFT
        for mg in message_groups:
            if mg['required'] and not mg['found']:
                table.append_row([
                    self.style.ERROR(mg['file']),
                    self.style.ERROR('Yes'),
                    self.style.ERROR('No')
                ])
            elif not mg['required'] and not mg['found']:
                found_txt = 'Yes'
                if not mg['found']:
                    found_txt = 'No'
                required_txt = 'Yes'
                if not mg['required']:
                    required_txt = 'No'
                table.append_row([mg['file'], required_txt, found_txt])
            else:
                found_txt = 'Yes'
                if not mg['found']:
                    found_txt = 'No'
                required_txt = 'Yes'
                if not mg['required']:
                    required_txt = 'No'

                table.append_row([
                    self.style.SUCCESS(mg['file']),
                    self.style.SUCCESS(required_txt),
                    self.style.SUCCESS(found_txt)
                ])

        self.stdout.write(str(table))
