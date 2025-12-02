# Add media to S3

Right now we have a local cache of Media. it may be useful to also have that in S3.
We would need a script to upload it to S3, and then update the archive_url field of the `post_media` to reflect this S3 path.
I am refering to S3 as the 'archive' in this case to reflect its permanence.

## AWS Specifics

AWS PROFILE : ab-power-user
BUCKET_NAME: s3://social-tui

Please design a reasonable bucket key path for this, so there is some amount of partitioning.

s3://social-tui/cache/{YYYY}/{MM}/{filename}.{ext}



