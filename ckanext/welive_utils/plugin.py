import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.logic.action import get, create, update, delete
from ckan.model.package import Package
from ckan.model.resource import Resource
from ckan.lib.base import c
from ckanext.welive.utils import generate_mapping
import logging
import ConfigParser
import os
import requests
import json
import time


config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

PLUGIN_SECTION = 'plugin:logging'
LOGGING_URL = config.get(PLUGIN_SECTION, 'logging_url')
APP_ID = config.get(PLUGIN_SECTION, 'app_id')

WELIVE_SECTION = 'plugin:welive_utils'
WELIVE_API = config.get(WELIVE_SECTION, 'welive_api')


log = logging.getLogger(__name__)


def send_log(context, pkg_dict, msg, _type, id_keyword):
    print pkg_dict
    current_time = time.time()
    log.debug('%s at %s' % (msg, current_time))
    user = context['auth_user_obj']
    custom_attr = {id_keyword: pkg_dict["id"]}
    if user is not None:
        custom_attr['UserID'] = user.id
    if 'title' in pkg_dict:
        if pkg_dict['title'] is not None:
            custom_attr['datasetName'] = pkg_dict['title']
    if 'ratings' in pkg_dict:
        if pkg_dict['ratings'] is not None:
            custom_attr['Rating'] = pkg_dict['ratings']
    if 'organization' in pkg_dict:
        custom_attr['CityName'] = pkg_dict['organization']['title']
    if 'type' in pkg_dict:
        if pkg_dict['type'] == 'dataset':
            if pkg_dict['private']:
                custom_attr['Type'] = 'Private'
            else:
                custom_attr['Type'] = 'Public'
    if 'extras' in pkg_dict:
        for extra in pkg_dict['extras']:
            if extra['key'] == 'source':
                custom_attr['Type'] = extra['value']

    data = {'msg': msg,
            'appId': APP_ID,
            'type': _type,
            'timestamp': current_time,
            'custom_attr': custom_attr
            }
    try:
        response = requests.post(LOGGING_URL + '/log/ods',
                                 data=json.dumps(data),
                                 headers={'Content-type': 'application/json'},
                                 verify=False)
        if response.status_code >= 400:
            log.debug(response.content)
    except:
        log.debug("Can't connect to logging service")


def send_dataset_log(context, pkg_dict, msg, _type):
    send_log(context, pkg_dict, msg, _type, 'DatasetID')


def send_resource_log(context, pkg_dict, msg, _type):
    send_log(context, pkg_dict, msg, _type, 'ResourceID')


def string_to_list(string_list):
    try:
        return eval(string_list)
    except:
        return []


def get_de_JSON(pkg_dict):
    tag_list = []
    for tag_dict in pkg_dict["tags"]:
        tag_list.append(tag_dict["name"])
    lang = None
    if 'extra' in pkg_dict:
        for extra in pkg_dict['extras']:
            if extra["key"] == 'language':
                lang = extra['value']
    if lang is None:
        if 'language' in pkg_dict:
            lang = pkg_dict['language']

    if lang is not None:
        data = {'lang': lang,
                'tags': tag_list
                }
        return json.dumps(data)
    return None


def update_de(pkg_dict):
    data_json = get_de_JSON(pkg_dict)
    if data_json is not None:
        log.debug('Creating metadata for dataset %s' % pkg_dict['id'])
        try:
            response = requests.put('%s/de/dataset/%s' %
                                    (WELIVE_API, pkg_dict['id']),
                                    data=data_json, verify=False
                                    )
            log.debug(data_json)
            log.debug(response.content)
        except:
            log.debug("Can't connect to Decision Engine")


def delete_de(pkg_dict):
    log.debug('Deleting metadata for dataset %s' % pkg_dict['id'])
    try:
        requests.delete('%s/de/dataset/%s' %
                        (WELIVE_API, pkg_dict['id']), verify=False)
    except:
        log.debug("Can't connect to Decision Engine")


@toolkit.side_effect_free
def package_show(context, data_dict):
    package_dict = get.package_show(context, data_dict)
    package = Package.get(package_dict['id'])
    package_dict['ratings'] = package.get_average_rating()
    # if package_dict['type'] == 'dataset':
    #     send_log(context, package_dict, 'Dataset metadata accessed',
    #              'DatasetMetadataAccessed')
    return package_dict


def package_create(context, data_dict):
    if type(data_dict) is dict:
        log.debug('Creating mapping...')
        mapped_resources = []
        if 'resources' in data_dict:
            for resource in data_dict['resources']:
                mapped_resource = generate_mapping(context, resource)
                mapped_resources.append(mapped_resource)
            data_dict['resources'] = mapped_resources

    package_dict = create.package_create(context, data_dict)
    package = None
    if type(package_dict) is not dict:
        package = get.package_show(context, {'id': package_dict})
    else:
        package = get.package_show(context, {'id': package_dict['id']})
    if package is not None:
        if package['type'] == 'dataset':
            send_dataset_log(context, package, 'Dataset created',
                             'DatasetPublished')
            update_de(package)

    return package_dict


def package_update(context, data_dict):
    mapped_resources = []
    if 'resources' in data_dict:
        for resource in data_dict['resources']:
            mapped_resource = generate_mapping(context, resource)
            mapped_resources.append(mapped_resource)
        data_dict['resources'] = mapped_resources

    package_dict = update.package_update(context, data_dict)
    if package_dict['type'] == 'dataset':
        send_dataset_log(context, package_dict, 'Dataset updated',
                         'DatasetMetadataUpdated')
        update_de(package_dict)
    return package_dict


def package_delete(context, data_dict):
    model = context['model']
    delete.package_delete(context, data_dict)
    package = Package.get(data_dict['id'])
    package.purge()
    model.repo.commit_and_remove()
    send_dataset_log(context, data_dict, 'Dataset removed',
                     'DatasetRemoved')
    delete_de(data_dict)
    return None


@toolkit.side_effect_free
def resource_show(context, data_dict):
    resource_dict = get.resource_show(context, data_dict)
    # send_resource_log(context, resource_dict, 'Resource metadata accessed',
    #                   'ResourceMetadataAccessed')

    return resource_dict


def resource_create(context, data_dict):
    if 'url' not in data_dict:
        url = ""
        data_dict['url'] = url
    resource_dict = create.resource_create(context, data_dict)
    send_resource_log(context, resource_dict, 'Resource created',
                      'ResourcePublished')

    return resource_dict


def resource_update(context, data_dict):
    log.debug(data_dict)
    model = context['model']
    resource = Resource.get(data_dict['id'])
    extras = resource.extras
    if resource is not None and 'url' not in data_dict:
        url = resource.url
        data_dict['url'] = url
    resource_dict = update.resource_update(context, data_dict)
    resource = Resource.get(data_dict['id'])
    if len(resource.extras) <= 0:
        resource.extras = extras
    model.repo.commit()
    for key in resource.extras:
        resource_dict[key] = resource.extras[key]

    send_resource_log(context, resource_dict, 'Resource metadata updated',
                      'ResourceMetadataUpdated')

    return resource_dict


def resource_delete(context, data_dict):
    delete.resource_delete(context, data_dict)
    send_resource_log(context, data_dict, 'Resource removed',
                      'ResourceRemoved')


def rating_create(context, data_dict):
    return_dict = create.rating_create(context, data_dict)
    package_dict = package_show(context, {'id': data_dict['package']})
    send_dataset_log(context, package_dict, 'Dataset updated',
                     'DatasetMetadataUpdated')
    return return_dict


def send_dataset_log_helper(pkg_dict, msg, _type):
    send_dataset_log({'auth_user_obj': c.userobj}, pkg_dict, msg, _type)


def send_resource_log_helper(resource_dict, msg, _type):
    send_resource_log({'auth_user_obj': c.userobj}, resource_dict, msg, _type)


class Welive_UtilsPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer, inherit=False)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IDatasetForm, inherit=False)
    plugins.implements(plugins.ITemplateHelpers)

    # ITemplateHelpers
    def get_helpers(self):
        return {'send_dataset_log_helper': send_dataset_log_helper,
                'send_resource_log_helper': send_resource_log_helper,
                'string_to_list': string_to_list}

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'welive_utils')

    # IActions

    def get_actions(self):
        return {'package_show': package_show,
                'package_create': package_create,
                'package_update': package_update,
                'package_delete': package_delete,
                'resource_show': resource_show,
                'resource_create': resource_create,
                'resource_update': resource_update,
                'resource_delete': resource_delete,
                'rating_create': rating_create}

    # IDatasetForm

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return False

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return ['dataset']

    def create_package_schema(self):
        schema = super(Welive_UtilsPlugin, self).create_package_schema()
        schema.update({
            'language': [toolkit.get_converter('convert_to_extras'),
                         toolkit.get_validator('ignore_missing')]
        })
        return schema

    def update_package_schema(self):
        schema = super(Welive_UtilsPlugin, self).update_package_schema()
        # our custom field
        schema.update({
            'language': [toolkit.get_converter('convert_to_extras'),
                         toolkit.get_validator('ignore_missing')]
        })
        return schema

    def show_package_schema(self):
        schema = super(Welive_UtilsPlugin, self).show_package_schema()
        schema.update({
            'language': [toolkit.get_converter('convert_from_extras'),
                         toolkit.get_validator('ignore_missing')]
        })
        return schema
