import mimetypes
from datetime import datetime

from boto.s3.connection import S3Connection
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets the Cache-Control header of all S3 files to a  max-age of 35 days"

    def handle(self, *args, **options):

        # Set up
        max_age_in_seconds = 60 * 60 * 24 * 35

        aws_storage_bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        s3_conn = S3Connection(
            settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY
        )

        bucket = s3_conn.get_bucket(aws_storage_bucket_name)

        # Count the number of files. Unfortunately, len() doesn't work
        # on the output of bucket.list().
        keys = bucket.list()
        num_keys = 0
        for key in keys:
            num_keys += 1

        # Now change the files.
        start_time = datetime.now()
        curr_count = 1
        for key in keys:
            key = bucket.get_key(key.name)
            metadata = key.metadata

            send_update = False

            new_cache_control = "max-age=%s,public" % max_age_in_seconds
            metadata["Cache-Control"] = new_cache_control
            if key.cache_control != new_cache_control:
                send_update = True

            (new_content_type, _) = mimetypes.guess_type(key.name)
            if new_content_type is not None:
                metadata["Content-Type"] = new_content_type
                if key.content_type != new_content_type:
                    send_update = True

            if send_update:

                if key.content_encoding:
                    metadata["Content-Encoding"] = key.content_encoding

                if key.content_disposition:
                    metadata["Content-Disposition"] = key.content_disposition

                if key.content_language:
                    metadata["Content-Language"] = key.content_language

                key.metadata = metadata
                key = key.copy(aws_storage_bucket_name, key, metadata=metadata)

            readable = False
            acl = key.get_acl()
            for grant in acl.acl.grants:
                if grant.permission == "READ":
                    if grant.uri == "http://acs.amazonaws.com/groups/global/AllUsers":
                        readable = True
            if not readable:
                print(("%s not public" % key.name))
                key.make_public()
                print(("%s now public" % key.name))

            timedelta_so_far = datetime.now() - start_time
            time_per_file = timedelta_so_far / curr_count
            count_remaining = num_keys - curr_count
            time_left = time_per_file * count_remaining

            cache_control_string = metadata.get("Cache-Control", None)
            content_type_string = metadata.get("Content-Type", None)

            print(
                (
                    "%s %s %s [file %s of %s, %s remaining]"
                    % (
                        key.name,
                        cache_control_string,
                        content_type_string,
                        curr_count,
                        num_keys,
                        time_left,
                    )
                )
            )
            curr_count += 1
