"""
.. module:: djangosnapshotpublisher.tests
   :synopsis: djangosnapshotpublisher unittest
"""

import json
import uuid

from django.core.management import call_command
from django.db.models.query import QuerySet
from django.test import TestCase
from django.utils import timezone

from djangosnapshotpublisher.models import (ContentRelease, ContentReleaseExtraParameter,
                                            ReleaseDocument)
from djangosnapshotpublisher.publisher_api import PublisherAPI, DATETIME_FORMAT


class PublisherAPITestCase(TestCase):
    """ unittest for PublisherAPITest with api_type=django """

    def setUp(self):
        """ setUp """
        self.publisher_api = PublisherAPI(api_type='django')
        self.datetime_past = timezone.now() - timezone.timedelta(minutes=10)
        self.datetime_future = timezone.now() + timezone.timedelta(minutes=10)

    def test_incorrect_api_type(self):
        """ test_incorrect_api_type """
        try:
            self.publisher_api = PublisherAPI(api_type='xml')
            self.fail('Value Error should be raised')
        except ValueError:
            pass

    def test_add_content_release(self):
        """ unittest for add_content_release """

        #  Create a ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title1', version='0.0.1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)
        response = self.publisher_api.set_stage_content_release('site1', content_release.uuid)
        response = self.publisher_api.set_live_content_release('site1', content_release.uuid)

        #  Try to create a ContentRelease that alredy exist
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_already_exists')

        #  Try to create a Base ContentRelease that alredy exist
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', None, uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'base_content_release_does_not_exist')

        #  Create a ContentRelease with Base ContentRelease
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', None, content_release.uuid)
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title2', version='0.0.2')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        #  Create a ContentRelease with extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.3', parameters, None, False)
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title2', version='0.0.3')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)
        extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release=content_release,
        )
        self.assertEqual(extra_parameters.count(), 2)
        for extra_parameter in extra_parameters:
            self.assertEqual(extra_parameter.content, parameters[extra_parameter.key])

    def test_remove_content_release(self):
        """ unittest for remove_content_release """

        #  Try to remove a ContentRelease that doesn't exist
        response = self.publisher_api.remove_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Create a ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = ContentRelease.objects.get(
            site_code='site1', title='title1', version='0.0.1')
        self.assertEqual(response['status'], 'success')

        #  Remove a ContentRelease
        response = self.publisher_api.remove_content_release('site1', content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertFalse(ContentRelease.objects.filter(
            site_code='site1', uuid=content_release.uuid).exists())

        #  Remove a ContentRelease with extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', parameters, None, False)
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.remove_content_release('site1', content_release.uuid)
        self.assertFalse(ContentRelease.objects.filter(
            site_code='site1', uuid=content_release.uuid).exists())
        self.assertFalse(ContentReleaseExtraParameter.objects.filter(
            content_release=content_release).exists())

    def test_update_content_release(self):
        """ unittest for update_content_release """

        #  Try to update a ContentRelease that doesn't exist
        response = self.publisher_api.update_content_release(
            'site1', uuid.uuid4(), **{'title': 'title1'})
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Update title and version for a ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.update_content_release('site1', content_release.uuid, **{
            'title': 'title2',
            'version': '0.0.2',
        })
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.title, 'title2')
        self.assertEqual(content_release.version, '0.0.2')

        #  Update without title and version
        response = self.publisher_api.update_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_title_version_not_defined')

        #  Update without extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.update_content_release('site1', content_release.uuid, **{
            'title': 'title3',
            'version': '0.0.2',
            'parameters': parameters,
        })
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.title, 'title3')
        self.assertEqual(content_release.version, '0.0.2')
        extra_parameters = ContentReleaseExtraParameter.objects.filter(
            content_release=content_release,
        )
        self.assertEqual(extra_parameters.count(), 2)
        for extra_parameter in extra_parameters:
            self.assertEqual(extra_parameter.content, parameters[extra_parameter.key])

    def test_get_content_release_details(self):
        """ unittest for get_content_release_details """

        #  Try to get a ContentRelease that doesn't exist
        response = self.publisher_api.get_content_release_details('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  get ContentRelease
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.get_content_release_details('site1', content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

    def test_get_content_release_details_query_parameters(self):
        """ unittest for get_content_release_details_query_parameters """

        #  missing parameters
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', None)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'parameters_missing')

        #  Try to get a ContentRelease that doesn't exist
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.1', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        # Get content release
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.1', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        # Get content release more than one same domain but different frontend
        parameters = {'frontend_id': 'v0.2', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.2', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)

        # Get content release more than one
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title3', '0.0.3', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_content_release_details_query_parameters(
            'site1', {'frontend_id': 'v0.1', 'domain': 'test.co.uk'})
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_more_than_one')

    def test_get_extra_paramater(self):
        """ unittest for test_get_extra_paramater """

        #  ContentReleaseExtraParameter doesn't exist
        response = self.publisher_api.get_extra_paramater('site1', uuid.uuid4(), 'frontend_id')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_extra_parameter_does_not_exist')

        # get extra parameter
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        content_release = response['content']
        response = self.publisher_api.get_extra_paramater(
            'site1', content_release.uuid, 'frontend_id')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], parameters['frontend_id'])

    def test_get_extra_paramaters(self):
        """ unittest for test_get_extra_paramater """

        #  No ContentReleaseExtraParameter
        response = self.publisher_api.get_extra_paramaters('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'success')
        self.assertEqual(type(response['content']), QuerySet)
        self.assertEqual(response['content'].count(), 0)

        # get extra parameters
        parameters1 = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters1, None, False)
        content_release = response['content']
        response = self.publisher_api.get_extra_paramaters('site1', content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 2)
        self.assertEqual(response['content'].get(
            key='frontend_id').content, parameters1['frontend_id'])
        self.assertEqual(response['content'].get(key='domain').content, parameters1['domain'])

        # update paramaters
        parameters2 = {'frontend_id': 'v0.2', 'domain_new': 'test.com'}
        response = self.publisher_api.update_content_release_parameters(
            'site1', content_release.uuid, parameters2)
        content_release_extra_parameter = ContentReleaseExtraParameter.objects.filter(
            content_release__uuid=content_release.uuid)
        self.assertEqual(content_release_extra_parameter.count(), 3)
        self.assertEqual(content_release_extra_parameter.get(
            key='domain').content, parameters1['domain'])
        self.assertEqual(content_release_extra_parameter.get(
            key='frontend_id').content, parameters2['frontend_id'])
        self.assertEqual(content_release_extra_parameter.get(
            key='domain_new').content, parameters2['domain_new'])

        # update paramaters with clear_first
        parameters3 = {'test1': 'value1', 'test2': 'value2'}
        self.publisher_api.update_content_release_parameters(
            'site1', content_release.uuid, parameters3, True)
        content_release_extra_parameter = ContentReleaseExtraParameter.objects.filter(
            content_release__uuid=content_release.uuid)
        self.assertEqual(content_release_extra_parameter.count(), 2)
        self.assertEqual(content_release_extra_parameter.get(
            key='test1').content, parameters3['test1'])
        self.assertEqual(content_release_extra_parameter.get(
            key='test2').content, parameters3['test2'])

        # update paramaters with wrong content_release
        response = self.publisher_api.update_content_release_parameters(
            'site1', uuid.uuid4(), parameters1, True)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

    def test_get_live_content_release(self):
        """ unittest for get_live_content_release """

        #  No ContentRelease
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')

        #  No ContentRelease in the past or null
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')
        content_release.publish_datetime = timezone.now() + timezone.timedelta(days=1)
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')

        #  ContentRelease in the past archived or PREVIEW
        content_release.publish_datetime = timezone.now() - timezone.timedelta(days=1)
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')
        content_release.status = 3
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1') 
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'no_content_release_live')

        #  Get live ContentRelease
        content_release.status = 2
        content_release.is_live = True
        content_release.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release)
        content_release.status = 3
        content_release.is_live = False
        content_release.save()

        #  Get latest live release
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        content_release2 = response['content']
        content_release2.status = 2
        content_release2.is_live = True
        content_release2.publish_datetime = timezone.now() - timezone.timedelta(hours=1)
        content_release2.save()
        response = self.publisher_api.get_live_content_release('site1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], content_release2)

    def test_set_live_content_release(self):
        """ unittest for set_live_content_release """

        #  No ContentRelease
        response = self.publisher_api.set_live_content_release('site1', uuid.uuid4())
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Set the ContentRelease live
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.set_stage_content_release('site1', content_release.uuid)
        response = self.publisher_api.set_live_content_release('site1', content_release.uuid)
        content_release = ContentRelease.objects.get(uuid=content_release.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.status, 2)
        self.assertGreater(timezone.now(), content_release.publish_datetime)
        self.assertGreater(
            content_release.publish_datetime,
            timezone.now() - timezone.timedelta(minutes=5)
        )

    # def test_freeze_content_release(self):
    #     """ unittest for freeze_content_release """

    #     #  No ContentRelease
    #     response = self.publisher_api.freeze_content_release(
    #         'site1',
    #         uuid.uuid4(),
    #         self.datetime_future,
    #     )
    #     self.assertEqual(response['status'], 'error')
    #     self.assertEqual(response['error_code'], 'content_release_does_not_exist')

    #     #  Wrong datetime format
    #     response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
    #     content_release = response['content']
    #     response = self.publisher_api.freeze_content_release(
    #         'site1',
    #         content_release.uuid,
    #         self.datetime_future.strftime('%H:%M:%S %d-%m-%Y'),
    #     )
    #     self.assertEqual(response['status'], 'error')
    #     self.assertEqual(response['error_code'], 'not_datetime')

    #     #  Publishdatetime in the past
    #     response = self.publisher_api.freeze_content_release(
    #         'site1',
    #         content_release.uuid,
    #         self.datetime_past,
    #     )
    #     self.assertEqual(response['status'], 'error')
    #     self.assertEqual(response['error_code'], 'publishdatetime_in_past')

    #     #  Freeze the ContentRelease
    #     response = self.publisher_api.freeze_content_release(
    #         'site1',
    #         content_release.uuid,
    #         self.datetime_future,
    #     )
    #     content_release = ContentRelease.objects.get(uuid=content_release.uuid)
    #     self.assertEqual(response['status'], 'success')
    #     self.assertEqual(content_release.status, 1)
    #     self.assertEqual(
    #         content_release.publish_datetime.strftime(DATETIME_FORMAT),
    #         self.datetime_future.strftime(DATETIME_FORMAT)
    #     )

#     def test_unfreeze_content_release(self):
#         """ unittest for unfreeze_content_release """

#         #  No ContentRelease
#         response = self.publisher_api.unfreeze_content_release('site1', uuid.uuid4())
#         self.assertEqual(response['status'], 'error')
#         self.assertEqual(response['error_code'], 'content_release_does_not_exist')

#         #  Unfreeze the ContentRelease
#         response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
#         content_release = response['content']
#         response = self.publisher_api.unfreeze_content_release('site1', content_release.uuid)
#         content_release = ContentRelease.objects.get(uuid=content_release.uuid)
#         self.assertEqual(response['status'], 'success')
#         self.assertEqual(content_release.status, 0)
#         content_release.publish_datetime = self.datetime_future
#         content_release.save()
#         content_release = ContentRelease.objects.get(uuid=content_release.uuid)
#         self.assertEqual(response['status'], 'success')
#         self.assertEqual(content_release.status, 0)

#         #  ContentRelease is published
#         content_release.publish_datetime = self.datetime_past
#         content_release.save()
#         response = self.publisher_api.unfreeze_content_release('site1', content_release.uuid)
#         self.assertEqual(response['status'], 'error')
#         self.assertEqual(response['error_code'], 'content_release_publish')

    # def test_archive_content_release(self):
    #     """ unittest for archive_content_release """

    #     #  No ContentRelease
    #     response = self.publisher_api.archive_content_release('site1', uuid.uuid4())
    #     self.assertEqual(response['status'], 'error')
    #     self.assertEqual(response['error_code'], 'content_release_does_not_exist')

    #     #  ContentRelease is not published
    #     response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
    #     content_release = response['content']
    #     response = self.publisher_api.archive_content_release('site1', content_release.uuid)
    #     self.assertEqual(response['status'], 'error')
    #     self.assertEqual(response['error_code'], 'content_release_not_publish')
    #     content_release.publish_datetime = self.datetime_future
    #     content_release.save()
    #     response = self.publisher_api.archive_content_release('site1', content_release.uuid)
    #     self.assertEqual(response['status'], 'error')
    #     self.assertEqual(response['error_code'], 'content_release_not_publish')

    #     #  Archive the ContentRelease
    #     content_release.publish_datetime = self.datetime_past
    #     content_release.save()
    #     response = self.publisher_api.archive_content_release('site1', content_release.uuid)
    #     content_release = ContentRelease.objects.get(uuid=content_release.uuid)
    #     self.assertEqual(response['status'], 'success')
    #     self.assertEqual(content_release.status, 3)

#     def test_unarchive_content_release(self):
#         """ unittest for unarchive_content_release """

#         #  No ContentRelease
#         response = self.publisher_api.unarchive_content_release('site1', uuid.uuid4())
#         self.assertEqual(response['status'], 'error')
#         self.assertEqual(response['error_code'], 'content_release_does_not_exist')

#         #  ContentRelease is not published
#         response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
#         content_release = response['content']
#         response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
#         self.assertEqual(response['status'], 'error')
#         self.assertEqual(response['error_code'], 'content_release_not_publish')
#         content_release.publish_datetime = self.datetime_future
#         content_release.save()
#         response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
#         self.assertEqual(response['status'], 'error')
#         self.assertEqual(response['error_code'], 'content_release_not_publish')

#         #  Unarchive the ContentRelease
#         content_release.publish_datetime = self.datetime_past
#         content_release.save()
#         response = self.publisher_api.unarchive_content_release('site1', content_release.uuid)
#         content_release = ContentRelease.objects.get(uuid=content_release.uuid)
#         self.assertEqual(response['status'], 'success')
#         self.assertEqual(content_release.status, 1)

    def test_list_content_releases(self):
        """ unittest for list_content_releases """

        #  No ContentRelease
        response = self.publisher_api.list_content_releases('site1')
        self.assertEqual(response['status'], 'success')
        self.assertFalse(response['content'].exists())

        #  List ContentReleases without defining status
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release1 = response['content']
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        response = self.publisher_api.list_content_releases('site1')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 2)

        #  List ContentReleases with status
        content_release1.status = 2
        content_release1.is_live = True
        content_release1.save()
        response = self.publisher_api.list_content_releases('site1', 2)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 1)

        #  List ContentReleases with status, and after a given time.
        self.publisher_api.set_stage_content_release('site1', content_release1.uuid)
        self.publisher_api.set_live_content_release('site1', content_release1.uuid)
        time_now = timezone.now()
        response = self.publisher_api.add_content_release('site1', 'title3', '0.0.3')
        content_release3 = response['content']
        self.publisher_api.set_stage_content_release('site1', content_release3.uuid)
        self.publisher_api.set_live_content_release('site1', content_release3.uuid)

        response = self.publisher_api.list_content_releases('site1', 2, time_now)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'].count(), 1)
        self.assertEqual(response['content'][0].title, 'title3')

    def test_get_document_from_content_release(self):
        """ unittest for get_document_from_content_release """

        document_key = 'key1'

        #  No ContentRelease
        response = self.publisher_api.get_document_from_content_release(
            'site1', uuid.uuid4(), document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  No ReleaseDocument
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')
        self.assertEqual(str(content_release), 'title1')

        #  Get ReleaseDocument
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        release_document = ReleaseDocument.objects.get(
            document_key=document_key,
            content_releases__id=content_release.id)
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], release_document)

        #  Get ReleaseDocument with content_type
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')
        release_document.content_type = 'page'
        release_document.save()
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], release_document)
        self.assertEqual(str(release_document), 'page - key1')

    def test_publish_document_to_content_release(self):
        """ unittest for publish_document_to_content_release """

        document_key = 'key1'

        #  No ContentRelease
        response = self.publisher_api.publish_document_to_content_release(
            'site1', uuid.uuid4(), '{}', document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  Store ReleaseDocument
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        document_json = json.dumps({'page_title': 'Test page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content']['created'], True)
        release_document = ReleaseDocument.objects.get(
            document_key=document_key, content_releases__id=content_release.id)
        self.assertEqual(release_document.document_json, document_json)

        #  Try to store a new ReleaseDocument with same  key and content_release
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content']['created'], False)
        release_document = ReleaseDocument.objects.get(
            document_key=document_key, content_releases__id=content_release.id)
        self.assertEqual(release_document.document_json, document_json)

        #  Store ReleaseDocument with content_type
        document_json = json.dumps({'page_title': 'Test3 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
            'page',
        )
        self.publisher_api.get_live_content_release('site1')
        release_document = ReleaseDocument.objects.get(
            document_key=document_key,
            content_releases__id=content_release.id,
            content_type='page')
        self.assertEqual(response['status'], 'success')
        response = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], release_document)

    def test_unpublish_document_from_content_release(self):
        """ unittest for unpublish_document_to_content_release """

        #  No ContentRelease
        document_key = 'key1'
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', uuid.uuid4(), document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #  No ReleaseDocument
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release = response['content']
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')

        #  Unpublish ReleaseDocument
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key)
        release_document = ReleaseDocument.objects.filter(
            document_key=document_key, content_releases__id=content_release.id)
        self.assertEqual(response['status'], 'success')
        self.assertFalse(release_document.exists())

        #  Unpublish ReleaseDocument content_type
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
            'page',
        )
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')
        response = self.publisher_api.unpublish_document_from_content_release(
            'site1', content_release.uuid, document_key, 'page')
        release_document = ReleaseDocument.objects.filter(
            document_key=document_key, content_releases__id=content_release.id, content_type='page')
        self.assertEqual(response['status'], 'success')
        self.assertFalse(release_document.exists())

    def test_compare_content_releases(self):
        """ unittest for compare_content_releases """

        #create release1 and documents
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release1 = response['content']
        document_json = json.dumps({'title': 'Test1'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key1',
        )
        document_json = json.dumps({'title': 'Test2'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key2',
        )

        #create release2 and documents
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        content_release2 = response['content']
        document_json = json.dumps({'title': 'Test3'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key2',
        )
        document_json = json.dumps({'title': 'Test4'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key3',
        )

        # Compare the releases but Wrong ContentRelease
        response = self.publisher_api.compare_content_releases(
            'site1', uuid.uuid4(), uuid.uuid4(),)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        # Compare the releases
        response = self.publisher_api.compare_content_releases(
            'site1', content_release2.uuid, content_release1.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key3',
                'content_type': 'content',
                'diff': 'Added',
            }, {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Changed',
            }, {
                'document_key': 'key1',
                'content_type': 'content',
                'diff': 'Removed',
            }
        ])

        #create release3 (rebase from 1) and documents
        self.publisher_api.set_stage_content_release('site1', content_release1.uuid)
        self.publisher_api.set_live_content_release('site1', content_release1.uuid)
        response = self.publisher_api.add_content_release(
            'site1', 'title3', '0.0.3', None, content_release1.uuid)
        content_release3 = response['content']
        document_json = json.dumps({'title': 'Test5'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release3.uuid,
            document_json,
            'key2',
        )
        document_json = json.dumps({'title': 'Test6'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release3.uuid,
            document_json,
            'key4',
        )

        response = self.publisher_api.compare_content_releases(
            'site1', content_release3.uuid, content_release1.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key4',
                'content_type': 'content',
                'diff': 'Added',
            }, {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Changed',
            }
        ])

        #create release4 (base on live release) and documents
        response = self.publisher_api.add_content_release(
            'site1', 'title4', '0.0.4', None, None, True)
        content_release4 = response['content']
        document_json = json.dumps({'title': 'Test7'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release4.uuid,
            document_json,
            'key2',
        )
        document_json = json.dumps({'title': 'Test8'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release4.uuid,
            document_json,
            'key5',
        )

        response = self.publisher_api.compare_content_releases(
            'site1', content_release4.uuid, content_release1.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key5',
                'content_type': 'content',
                'diff': 'Added',
            }, {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Changed',
            }
        ])

        #create release4 with release3
        response = self.publisher_api.compare_content_releases(
            'site1', content_release4.uuid, content_release3.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key5',
                'content_type': 'content',
                'diff': 'Added',
            }, {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Changed',
            }, {
                'document_key': 'key4',
                'content_type': 'content',
                'diff': 'Removed'
            }
        ])

        #create release4 (base on live release) and documents
        response = self.publisher_api.set_stage_content_release('site1', content_release4.uuid)
        response = self.publisher_api.set_live_content_release('site1', content_release4.uuid)

        response = self.publisher_api.add_content_release(
            'site1', 'title5', '0.0.5', None, None, True)
        content_release5 = response['content']
        document_json = json.dumps({'title': 'Test7'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release5.uuid,
            document_json,
            'key2',
        )
        document_json = json.dumps({'title': 'Test9'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release5.uuid,
            document_json,
            'key5',
        )

        response = self.publisher_api.compare_content_releases(
            'site1', content_release5.uuid, content_release4.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Changed',
            }, {
                'document_key': 'key5',
                'content_type': 'content',
                'diff': 'Changed',
            }
        ])

    def test_delete_document_from_content_release(self):
        """ unittest for compare_content_releases """

        #create release1 and documents
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release1 = response['content']

        #add key1, key2, key3 and key4 to release1
        document_json = json.dumps({'title': 'Test1'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key1',
        )
        document_json = json.dumps({'title': 'Test2'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key2',
        )
        document_json = json.dumps({'title': 'Test3'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key3',
        )
        document_json = json.dumps({'title': 'Test4'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key4',
        )
        self.publisher_api.set_stage_content_release('site1', content_release1.uuid)
        self.publisher_api.set_live_content_release('site1', content_release1.uuid)

        #create release2 and documents
        response = self.publisher_api.add_content_release(
            'site1', 'title2', '0.0.2', None, None, True)
        content_release2 = response['content']

        #add key5 to release2
        document_json = json.dumps({'title': 'Test5'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key5',
        )

        #update key1 to release2 then delete it
        document_json = json.dumps({'title': 'Test1.1'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key1',
        )

        response = self.publisher_api.delete_document_from_content_release(
            'site1',
            content_release2.uuid,
            'key1',
        )
        self.assertEqual(response['status'], 'success')

        # try to delete wrong ContentRelease
        response = self.publisher_api.delete_document_from_content_release(
            'site1',
            uuid.uuid4(),
            'key1',
        )
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        #update key3 to release2
        document_json = json.dumps({'title': 'Test3.1'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key3',
        )

        #delete key2 to release2
        response = self.publisher_api.delete_document_from_content_release(
            'site1',
            content_release2.uuid,
            'key2',
        )
        self.assertEqual(response['status'], 'success')

        #delete then update key4 to release2
        response = self.publisher_api.delete_document_from_content_release(
            'site1',
            content_release2.uuid,
            'key4',
        )
        self.assertEqual(response['status'], 'success')
        document_json = json.dumps({'title': 'Test4.1'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key4',
        )

        # compare release2 to release1
        response = self.publisher_api.compare_content_releases(
            'site1', content_release2.uuid, content_release1.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key5',
                'content_type': 'content',
                'diff': 'Added',
            }, {
                'document_key': 'key3',
                'content_type': 'content',
                'diff': 'Changed',
            }, {
                'document_key': 'key4',
                'content_type': 'content',
                'diff': 'Changed',
            }, {
                'document_key': 'key1',
                'content_type': 'content',
                'diff': 'Removed',
            }, {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Removed',
            }
        ])

    def test_compare_content_releases_with_paramters(self):
        """ unittest for compare_content_releases """

        #create release1 and documents
        response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        content_release1 = response['content']
        document_json = json.dumps({'title': 'Test1'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key1',
            'content',
            {'p1': 'test1', 'p2': 'test2'},
        )
        document_json = json.dumps({'title': 'Test2'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release1.uuid,
            document_json,
            'key2',
            'content',
            {'p1': 'test3', 'p2': 'test4'},
        )

        #create release2 and documents
        response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
        content_release2 = response['content']
        document_json = json.dumps({'title': 'Test3'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key2',
            'content',
            {'p1': 'test5', 'p2': 'test6'},
        )
        document_json = json.dumps({'title': 'Test4'})
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release2.uuid,
            document_json,
            'key3',
            'content',
            {'p1': 'test7', 'p2': 'test8'},
        )

        # Compare the releases
        response = self.publisher_api.compare_content_releases(
            'site1', content_release2.uuid, content_release1.uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], [
            {
                'document_key': 'key3',
                'content_type': 'content',
                'diff': 'Added',
                'parameters': {'p1': 'test7', 'p2': 'test8'},
            }, {
                'document_key': 'key2',
                'content_type': 'content',
                'diff': 'Changed',
                'parameters': {
                    'release_from': {'p1': 'test5', 'p2': 'test6'},
                    'release_compare_to': {'p1': 'test3', 'p2': 'test4'},
                }
            }, {
                'document_key': 'key1',
                'content_type': 'content',
                'diff': 'Removed',
                'parameters': {'p1': 'test1', 'p2': 'test2'},
            }
        ])


class PublisherAPIJsonTestCase(TestCase):
    """ unittest for PublisherAPIJsonTest with api_type=json """

    def setUp(self):
        """ setUp """
        self.publisher_api = PublisherAPI(api_type='json')

    def test_add_content_release(self):
        """ unittest for add_content_release """

        #  Create a ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'uuid': response['content']['uuid'],
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PREVIEW',
            'publish_datetime': None,
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

        #  Try to create a ContentRelease that alredy exist
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_already_exists')

    def test_remove_content_release(self):
        """ unittest for remove_content_release """

        #  Create a ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release_uuid = response['content']['uuid']
        #  Remove a ContentRelease
        response_json = self.publisher_api.remove_content_release('site1', content_release_uuid)
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertFalse(ContentRelease.objects.filter(
            site_code='site1', uuid=content_release_uuid).exists())

    def test_update_content_release(self):
        """ unittest for update_content_release """

        #  Update title and version for a ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release_uuid = response['content']['uuid']
        response = self.publisher_api.update_content_release('site1', content_release_uuid, **{
            'title': 'title2',
            'version': '0.0.2',
        })
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=content_release_uuid)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(content_release.title, 'title2')
        self.assertEqual(content_release.version, '0.0.2')

    def test_get_content_release_details(self):
        """ unittest for get_content_release_details """

        #  get ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        self.assertEqual(response['status'], 'success')
        response_json = self.publisher_api.get_content_release_details(
            'site1', content_release.uuid)
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PREVIEW',
            'publish_datetime': None,
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

    def test_get_live_content_release(self):
        """ unittest for get_live_content_release """

        #  Get live ContentRelease
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        content_release.status = 2
        content_release.is_live = True
        content_release.publish_datetime = timezone.now() - timezone.timedelta(hours=1)
        content_release.save()
        response_json = self.publisher_api.get_live_content_release('site1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'LIVE',
            'publish_datetime': response['content']['publish_datetime'],
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

    def test_list_content_releases(self):
        """ unittest for list_content_releases """

        #  List Releases without defining status
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        response_json = self.publisher_api.list_content_releases('site1')
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(len(response['content']), 1)
        self.assertEqual(response['content'][0], {
            'uuid': str(content_release.uuid),
            'version': '0.0.1',
            'title': 'title1',
            'site_code': 'site1',
            'status': 'PREVIEW',
            'publish_datetime': response['content'][0]['publish_datetime'],
            'use_current_live_as_base_release': False,
            'base_release': None,
        })

    def test_get_document_from_content_release(self):
        """ unittest for get_document_from_content_release """

        document_key = 'key1'
        response_json = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
        response = json.loads(response_json)
        content_release = ContentRelease.objects.get(uuid=response['content']['uuid'])
        document_json = json.dumps({'page_title': 'Test2 page title'})
        response_json = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release.uuid,
            document_json,
            document_key,
        )
        response_json = self.publisher_api.get_document_from_content_release(
            'site1', content_release.uuid, document_key)
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], {
            'document_key': document_key,
            'document_json': document_json,
            'content_type': 'content',
            'deleted': False,
        })

    def test_get_extra_paramaters(self):
        """ unittest for test_get_extra_paramater """

        # get extra parameters
        parameters = {'frontend_id': 'v0.1', 'domain': 'test.co.uk'}
        response_json = self.publisher_api.add_content_release(
            'site1', 'title1', '0.0.1', parameters, None, False)
        response = json.loads(response_json)
        content_release = response['content']
        response_json = self.publisher_api.get_extra_paramaters('site1', content_release['uuid'])
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')

        content = response['content']
        content.sort(key=lambda item: item['key'])

        self.assertEqual(content, [
            {
                'key': 'domain',
                'content': 'test.co.uk',
                'content_release_uuid': content_release['uuid']
            }, {
                'key': 'frontend_id',
                'content': 'v0.1',
                'content_release_uuid': content_release['uuid']
            },
        ])

        # get document extra parameters but Wrong ContentRelease
        response_json = self.publisher_api.get_document_extra_from_content_release(
            'site1',
            uuid.uuid4(),
            'key1',
            'page',
        )
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'content_release_does_not_exist')

        # get document extra parameters but Wrong ReleaseDocument
        response_json = self.publisher_api.get_document_extra_from_content_release(
            'site1',
            content_release['uuid'],
            'wrong_key',
            'page',
        )
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error_code'], 'release_document_does_not_exist')

        # get document extra parameters
        document_json = json.dumps({'page_title': 'Test page title'})
        parameters = {'para1': 'test1', 'para2': 'test2'}
        response = self.publisher_api.publish_document_to_content_release(
            'site1',
            content_release['uuid'],
            document_json,
            'key1',
            'page',
            parameters,
        )

        response_json = self.publisher_api.get_document_extra_from_content_release(
            'site1',
            content_release['uuid'],
            'key1',
            'page',
        )
        response = json.loads(response_json)
        self.assertEqual(response['status'], 'success')

        content = response['content']
        content.sort(key=lambda item: item['key'])

        self.assertEqual(content, [
            {
                'key': 'para1',
                'content': 'test1',
            }, {
                'key': 'para2',
                'content': 'test2',
            },
        ])


class PublisherScriptTestCase(TestCase):
    """ unittest for PublisherScriptTest with api_type=django """

    def setUp(self):
        """ setUp """
        self.publisher_api = PublisherAPI(api_type='django')
        self.datetime_past = timezone.now() - timezone.timedelta(minutes=10)
        self.datetime_future = timezone.now() + timezone.timedelta(minutes=10)

    # def test_schedule_publish_date(self):
    #     """ test_schedule_publish_date """

    #     #  Create ContentReleases
    #     response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
    #     content_release1 = response['content']
    #     response = self.publisher_api.add_content_release('site1', 'title2', '0.0.2')
    #     content_release2 = response['content']
    #     response = self.publisher_api.add_content_release('site1', 'title3', '0.0.3')
    #     content_release3 = response['content']

    #     response = self.publisher_api.add_content_release('site2', 'title4', '0.0.1')
    #     content_release4 = response['content']
    #     response = self.publisher_api.add_content_release('site2', 'title5', '0.0.2')
    #     content_release5 = response['content']
    #     response = self.publisher_api.add_content_release('site2', 'title6', '0.0.3')
    #     content_release6 = response['content']

    #     content_release1.publish_datetime = self.datetime_past
    #     content_release1.status = 1
    #     content_release1.save()

    #     content_release2.publish_datetime = self.datetime_past
    #     content_release2.status = 1
    #     content_release2.save()

    #     content_release3.publish_datetime = self.datetime_future
    #     content_release3.status = 1
    #     content_release3.save()

    #     content_release4.publish_datetime = self.datetime_past
    #     content_release4.status = 1
    #     content_release4.save()

    #     content_release5.publish_datetime = self.datetime_future
    #     content_release5.status = 1
    #     content_release5.save()

    #     content_release6.publish_datetime = self.datetime_past
    #     content_release6.status = 1
    #     content_release6.save()

    #     call_command('release_publisher')

    #     live_content_release_site1 = ContentRelease.objects.filter(
    #         is_live=True,
    #         site_code='site1',
    #     ).order_by('title').values_list('title', flat=True)

    #     self.assertEqual(list(live_content_release_site1), ['title1', 'title2'])

    #     live_content_release_site2 = ContentRelease.objects.filter(
    #         is_live=True,
    #         site_code='site2',
    #     ).order_by('title').values_list('title', flat=True)

    #     self.assertEqual(list(live_content_release_site2), ['title4', 'title6'])

    # def test_set_live(self):
    #     """ test_set_live """

    #     #  Create ContentReleases
    #     response = self.publisher_api.add_content_release('site1', 'title1', '0.0.1')
    #     content_release1 = response['content']

    #     self.publisher_api.set_live_content_release('site1', content_release1.uuid)
    #     self.publisher_api.set_live_content_release('site1', content_release1.uuid)

    #     ContentRelease.objects.get(
    #         is_live=False,
    #         id=content_release1.id
    #     )

    #     call_command('release_publisher')

    #     ContentRelease.objects.get(
    #         is_live=True,
    #         id=content_release1.id
    #     )
