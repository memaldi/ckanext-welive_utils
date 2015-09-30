import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.logic.action import delete
from ckan.logic.action import update
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
    resource = Resource.get(data_dict['id'])
    if resource is not None and 'url' not in data_dict:
        url = resource.url
        data_dict['url'] = url
        log.debug(url)
    log.debug(data_dict)
    package_dict = update.resource_update(context, data_dict)
    return package_dict


class Welive_UtilsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'welive_utils')

    # IActions

    def get_actions(self):
        return {'package_delete': package_delete,
                'resource_update': resource_update}
