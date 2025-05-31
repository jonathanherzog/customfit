# import mimetypes
# from datetime import datetime


import boto3
from django.conf import settings
from django.core.management.base import BaseCommand

# from boto.s3.connection import S3Connection, OrdinaryCallingFormat
# from boto.s3.cors import  CORSConfiguration


class Command(BaseCommand):
    """
    A command-line tool to set the CORS policy on an S3 bucket.
    CORS stands for Cross-origin resource sharing and needs to be set properly
    so that browsers know that they can safely bypass their defenses against
    cross-site scripting attacks. (See
    http://en.wikipedia.org/wiki/Cross-origin_resource_sharing) Without this,
    we run into problems where browsers refuse to load fonts in our S3 bucket
    that are referenced in our CSS and JS.
    """

    help = "Sets the CORS policy on the S3 bucket in use"

    def handle(self, *args, **options):

        production_hosts = [
            # FILL ME IN
        ]

        testing_hosts = [
            # FILL ME IN
        ]

        # Change 'some_bucket' below, to a real bucket
        bucket_to_host_dict = {
            "some_bucket": sum(
                [
                    production_hosts,
                    # We include the next line becuase
                    # this bucket has error-page assets
                    # that might be needed on the testing &
                    # staging servers
                    testing_hosts,
                ],
                [],
            ),
        }

        # Prepend http:// and https:// to each server name in the dict.

        for bucket_name, server_list in list(bucket_to_host_dict.items()):
            new_server_list = []
            for server in server_list:
                if server == "*":
                    new_server_list.append(server)
                else:
                    new_server_list.append("http://" + server)
                    new_server_list.append("https://" + server)

            bucket_to_host_dict[bucket_name] = new_server_list

        aws_storage_bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        s3 = boto3.client("s3")
        current_cors = s3.get_bucket_cors(Bucket=aws_storage_bucket_name)
        new_cors = []
        current_cors = current_cors["CORSRules"]
        hosts = bucket_to_host_dict[aws_storage_bucket_name]
        for item in current_cors:
            for host in hosts:
                if host not in item["AllowedOrigins"]:
                    item["AllowedOrigins"].append(host)
        new_cors.append(item)
        new_cors = {"CORSRules": new_cors}

        s3.put_bucket_cors(Bucket=aws_storage_bucket_name, CORSConfiguration=new_cors)
