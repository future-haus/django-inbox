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

        used_template_names = []
        message_groups = []
        for message_group in inbox_settings.get_config()['MESSAGE_GROUPS']:
            for k, v in message_group['preference_defaults'].items():
                if v is not None:

                    for message_key in message_group['message_keys']:
                        template_names = MessageLog._get_subject_template_names(message_key, None, True)
                        template_names.extend(MessageLog._get_body_template_names(message_key, None, True))
                        template_names.extend(MessageLog._get_subject_template_names(message_key, MessageMedium.get(k.upper()), True))
                        template_names.extend(MessageLog._get_body_template_names(message_key, MessageMedium.get(k.upper()), True))

                        for template_name, required in template_names:
                            if template_name in used_template_names:
                                continue

                            used_template_names.append(template_name)

                            try:
                                loader.get_template(template_name)
                            except TemplateDoesNotExist:
                                message_groups.append({
                                                           'file': template_name,
                                                           'key': message_key,
                                                           'medium': k.lower(),
                                                           'required': required,
                                                           'found': False
                                                              })
                            else:
                                message_groups.append({
                                                           'file': template_name,
                                                           'key': message_key,
                                                           'medium': k.lower(),
                                                           'required': required,
                                                           'found': True
                                                              })

        table = BeautifulTable()
        table.column_headers = ['File', 'Required', 'Found']
        table.column_alignments['File'] = BeautifulTable.ALIGN_LEFT

        table_optional = BeautifulTable()
        table_optional.column_headers = ['File (Optional)', 'Required', 'Found']
        table_optional.column_alignments['File (Optional)'] = BeautifulTable.ALIGN_LEFT

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
                table_optional.append_row([mg['file'], required_txt, found_txt])
            else:
                found_txt = 'Yes'
                if not mg['found']:
                    found_txt = 'No'
                required_txt = 'Yes'
                if not mg['required']:
                    required_txt = 'No'

                if mg['required']:
                    table.append_row([
                        self.style.SUCCESS(mg['file']),
                        self.style.SUCCESS(required_txt),
                        self.style.SUCCESS(found_txt)
                    ])
                else:
                    table_optional.append_row([
                        self.style.SUCCESS(mg['file']),
                        self.style.SUCCESS(required_txt),
                        self.style.SUCCESS(found_txt)
                    ])

        final_table = BeautifulTable()
        final_table.column_headers = ['File', 'Required', 'Found']
        final_table.column_alignments['File'] = BeautifulTable.ALIGN_LEFT

        for row in table:
            final_table.append_row(row)

        final_table.append_row([
            'File (Optional)', 'Required', 'Found'
        ])

        for row in table_optional:
            final_table.append_row(row)

        self.stdout.write(str(final_table))
