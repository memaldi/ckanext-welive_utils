import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.logic.action import delete
from ckan.logic.action import update
from ckan.logic.action import create
from ckan.model.package import Package
from ckan.model.resource import Resource
import logging

log = logging.getLogger(__name__)


def package_delete(context, data_dict):
    model = context['model']
    delete.package_delete(context, data_dict)
    package = Package.get(data_dict['id'])
    package.purge()
    model.repo.commit_and_remove()
    return None


def resource_update(context, data_dict):
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
    return resource_dict


def resource_create(context, data_dict):
    if 'url' not in data_dict:
        url = ""
        data_dict['url'] = url
    package_dict = create.resource_create(context, data_dict)
    return package_dict


class Welive_UtilsPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer, inherit=False)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IDatasetForm, inherit=False)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'welive_utils')

    # IActions

    def get_actions(self):
        return {'package_delete': package_delete,
                'resource_update': resource_update,
                'resource_create': resource_create
                }

    # IDatasetForm

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return ['dataset']

    def create_package_schema(self):
        schema = super(Welive_UtilsPlugin, self).create_package_schema()
        schema.update({
            'language': [toolkit.get_converter('convert_to_extras')]
        })
        return schema

    def update_package_schema(self):
        schema = super(Welive_UtilsPlugin, self).update_package_schema()
        # our custom field
        schema.update({
            'language': [toolkit.get_converter('convert_to_extras')]
        })
        return schema

    def show_package_schema(self):
        schema = super(Welive_UtilsPlugin, self).show_package_schema()
        schema.update({
            'language': [toolkit.get_converter('convert_from_extras')]
        })
        return schema
