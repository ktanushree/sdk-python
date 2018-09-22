"""
Python2 and Python3 SDK for the CloudGenix AppFabric

**Version:** v5.0.3b1

**Author:** CloudGenix

**Copyright:** (c) 2017, 2018 CloudGenix, Inc

**License:** MIT

**Location:** <https://github.com/CloudGenix/sdk-python>

#### Synopsis
Intended to be a small, lightweight SDK wrapper around the CloudGenix API for easy use.
Initial version requires knowledge of JSON/Dict objects for POST/PUT/PATCH operations.

#### Requirements
* Active CloudGenix Account
* Python >= 2.7 or >=3.6
* Python modules:
    * Requests + Security Extras >=2.18.4 - <http://docs.python-requests.org/en/master/>

#### Code Example
Super-simplified example code (rewrite of example.py in ~4 lines of code):

    #!python
    # Import the CloudGenix SDK API constructor and JSON response pretty printer
    from cloudgenix import API, jd

    # Instantiate the CloudGenix API constructor
    cgx_sess = API()

    # Call CloudGenix API login using the Interactive helpers (Handle SAML2.0 login and MSP functions too!).
    cgx_sess.interactive.login()

    # Print a dump of the list of sites for your selected account
    jd(cgx_sess.get.sites())

#### License
MIT

#### For more info
 * Get help and additional CloudGenix Documentation at <http://support.cloudgenix.com>
 * View the autogenerated documentation in the `docs/` directory, or at <https://cloudgenix.github.io/sdk-python/>.
 * View in-python help using `help()` functions. (example: `help(cgx_sess.get.login)`)

"""
from __future__ import unicode_literals
import logging
import os
import json
from time import sleep
import re
import atexit
import sys

import requests
from requests.packages import urllib3

from .get_api import Get
from .post_api import Post
from .patch_api import Patch
from .put_api import Put
from .delete_api import Delete
from .interactive import Interactive

# CA Certificate bundle
from tempfile import NamedTemporaryFile as temp_ca_bundle
from .ca_bundle import CG_CA_BUNDLE as _CG_CA_BUNDLE

# python 2 and 3 handling
if sys.version_info < (3,):
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes

BYTE_CA_BUNDLE = binary_type(_CG_CA_BUNDLE)
"""
Explicit CA bundle for CA Pinning - Root Certificates for the CloudGenix Controller API Endpoint.

Loaded from `cloudgenix.ca_bundle.CG_CA_BUNDLE`
"""

__author__ = "CloudGenix Developer Support <developers@cloudgenix.com>"
__email__ = "developers@cloudgenix.com"
__copyright__ = "Copyright (c) 2017, 2018 CloudGenix, Inc"
__license__ = """
    MIT License
    
    Copyright (c) 2017, 2018 CloudGenix, Inc
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""

# Set logging to function name
api_logger = logging.getLogger(__name__)
"""logging.getlogger object to enable debug printing via `cloudgenix.API.set_debug`"""

# Version of SDK
version = "5.0.3b1"
"""SDK Version string"""

# PyPI URL for checking for updates.
update_info_url = "https://pypi.org/pypi/cloudgenix/json"
"""URL for checking for updates."""


# regex
SDK_BUILD_REGEX = re.compile(
    r'^'                        # start of string
    r'(?P<major>[0-9]+)'        # major number
    r'\.'                       # literal . character
    r'(?P<minor>[0-9]+)'        # minor number
    r'\.'                       # literal . character
    r'(?P<patch>[0-9]+)'        # patch number
    r'b'                        # literal 'b' character
    r'(?P<build>[0-9]+)'        # build number
    r'$'                        # end of string
)
"""REGEX for parsing SDK builds"""


def jd(api_response):
    """
    JD (JSON Dump) function. Meant for quick pretty-printing of a CloudGenix Response body.

    Example: `jd(cgx_sess.get.sites())`

      **Parameters:**

      - **api_response:** A CloudGenix-attribute extended `requests.Response` object

    **Returns:** No Return, directly prints all output.
    """
    print(jdout(api_response))
    return


def jdout(api_response):
    """
    JD Output function. Does quick pretty printing of a CloudGenix Response body. This function returns a string
    instead of directly printing content.

      **Parameters:**

      - **api_response:** A CloudGenix-attribute extended `requests.Response` object

    **Returns:** Pretty-formatted text of the Response body
    """
    try:
        # attempt to output the cgx_content. should always be a Dict if it exists.
        output = json.dumps(api_response.cgx_content, indent=4)
    except (TypeError, ValueError, AttributeError):
        # cgx_content did not exist, or was not JSON serializable. Try pretty output the base obj.
        try:
            output = json.dumps(api_response, indent=4)
        except (TypeError, ValueError, AttributeError):
            # Same issue, just raw output the passed data. Let any exceptions happen here.
            output = api_response
    return output


def jd_detailed(api_response, sensitive=False):
    """
    JD (JSON Dump) Detailed function. Meant for quick DETAILED pretty-printing of CloudGenix Request and Response
    objects for troubleshooting.

    Example: `jd_detailed(cgx_sess.get.sites())`

      **Parameters:**

      - **api_response:** A CloudGenix-attribute extended `requests.Response` object
      - **sensitive:** Boolean, if True will print sensitive content (specifically, authentication cookies/headers).

    **Returns:** No Return, directly prints all output.
    """
    print(jdout_detailed(api_response, sensitive=sensitive))
    return


def jdout_detailed(api_response, sensitive=False):
    """
    JD Output Detailed function. Meant for quick DETAILED pretty-printing of CloudGenix Request and Response
    objects for troubleshooting. This function returns a string instead of directly printing content.

      **Parameters:**

      - **api_response:** A CloudGenix-attribute extended `requests.Response` object
      - **sensitive:** Boolean, if True will print sensitive content (specifically, authentication cookies/headers).

    **Returns:** Pretty-formatted text of the Request, Request Headers, Request body, Response, Response Headers,
    and Response Body.
    """
    try:
        # try to be super verbose.
        output = "REQUEST: {0} {1}\n".format(api_response.request.method, api_response.request.path_url)
        output += "REQUEST HEADERS:\n"
        for key, value in api_response.request.headers.items():
            # look for sensitive values
            if key.lower() in ['cookie'] and not sensitive:
                # we need to do some work to watch for the AUTH_TOKEN cookie. Split on cookie separator
                cookie_list = value.split('; ')
                muted_cookie_list = []
                for cookie in cookie_list:
                    # check if cookie starts with a permutation of AUTH_TOKEN/whitespace.
                    if cookie.lower().strip().startswith('auth_token='):
                        # first 11 chars of cookie with whitespace removed + mute string.
                        newcookie = cookie.strip()[:11] + "\"<SENSITIVE - NOT SHOWN BY DEFAULT>\""
                        muted_cookie_list.append(newcookie)
                    else:
                        muted_cookie_list.append(cookie)
                # got list of cookies, muted as needed. recombine.
                muted_value = "; ".join(muted_cookie_list)
                output += "\t{0}: {1}\n".format(key, muted_value)
            elif key.lower() in ['x-auth-token'] and not sensitive:
                output += "\t{0}: {1}\n".format(key, "<SENSITIVE - NOT SHOWN BY DEFAULT>")
            else:
                output += "\t{0}: {1}\n".format(key, value)
        # if body not present, output blank.
        if not api_response.request.body:
            output += "REQUEST BODY:\n{0}\n\n".format({})
        else:
            try:
                # Attempt to load JSON from string to make it look beter.
                output += "REQUEST BODY:\n{0}\n\n".format(json.dumps(json.loads(api_response.request.body), indent=4))
            except (TypeError, ValueError, AttributeError):
                # if pretty call above didn't work, just toss it to jdout to best effort it.
                output += "REQUEST BODY:\n{0}\n\n".format(jdout(api_response.request.body))
        output += "RESPONSE: {0} {1}\n".format(api_response.status_code, api_response.reason)
        output += "RESPONSE HEADERS:\n"
        for key, value in api_response.headers.items():
            output += "\t{0}: {1}\n".format(key, value)
        try:
            # look for CGX content first.
            output += "RESPONSE DATA:\n{0}".format(json.dumps(api_response.cgx_content, indent=4))
        except (TypeError, ValueError, AttributeError):
            # look for standard response data.
            output += "RESPONSE DATA:\n{0}".format(json.dumps(json.loads(api_response.content), indent=4))
    except (TypeError, ValueError, AttributeError, UnicodeDecodeError):
        # cgx_content did not exist, or was not JSON serializable. Try pretty output the base obj.
        try:
            output = json.dumps(api_response, indent=4)
        except (TypeError, ValueError, AttributeError):
            # Same issue, just raw output the passed data. Let any exceptions happen here.
            output = api_response
    return output


class API(object):
    """
    Class for interacting with the CloudGenix API.

    Subclass objects are linked to various operations.

     - get: links to `cloudgenix.get_api.Get` for API Get Operations
     - post: links to `cloudgenix.post_api.Post` for API Post Operations
     - put: links to `cloudgenix.put_api.Put` for API Put Operations
     - patch: links to `cloudgenix.patch_api.Patch` for API Patch Operations
     - delete: links to `cloudgenix.delete_api.Delete` for API Delete Operations
    """
    # Global structure, previously sdk_vars
    # Authentication is now stored as cookies, as part of the requests.Session() object.
    controller = 'https://api.elcapitan.cloudgenix.com'
    """Current active controller URL"""

    controller_orig = None
    """Original Controller URL as entered - before Region re-parse"""

    controller_region = None
    """Controller Region, if present."""

    ignore_region = False
    """Ignore regions returned by controller, and use explicit controller only."""

    _debuglevel = 0
    """debug level - set via set_debug()"""

    tenant_id = None
    """Numeric ID of tenant (account) - should be set after initial login from `cloudgenix.get_api.Get.profile` data"""

    tenant_name = None
    """Name of tenant (account), should be set after initial login from `cloudgenix.get_api.Get.profile` data"""

    token_session = None
    """Is this login from a static AUTH_TOKEN (True), or a standard login (False)"""

    is_esp = None
    """Is the current tenant an ESP/MSP?"""

    client_id = None
    """If ESP/MSP, is client currently logged in"""

    address_string = None
    """String representing address, optional - should be pulled from get.profile() data."""

    email = None
    """Email (userrname) for session"""

    _user_id = None
    """user_id for passed user info"""

    _password = None
    """user password - only used when argv passed, and cleared quickly"""

    roles = None
    """Roles list"""

    verify = True
    """Verify SSL certificate."""

    version = None
    """Version string for use once Constructor created."""

    ca_verify_filename = None
    """Filename to use for CA verification."""

    _ca_verify_file_handle = None
    """File handle for CA verification"""

    rest_call_retry = False
    """Boolean to Automatically retry failed REST calls. (Should NOT be True for APIs that CREATE objects.)"""

    rest_call_max_retry = 30
    """REST call maximum retry attempts."""

    rest_call_sleep = 10
    """Seconds to wait between REST retries."""

    rest_call_timeout = 60
    """Maximum time to wait for any data from REST server."""

    cache = {}
    """API response cache (Future)"""

    _parent_namespace = None
    """holder for namespace for wrapper classes."""

    _session = None
    """holder for requests.Session() object"""

    update_check = True
    """Notify users of available update to SDK"""

    update_info_url = None
    """Update Info URL for use once Constructor Created."""

    def __init__(self, controller=controller, ssl_verify=verify, update_check=True):
        """
        Create the API constructor object

          - **controller:** Initial Controller URL String
          - **ssl_verify:** Should SSL be verified for this system. Can be file or BOOL. See `cloudgenix.API.ssl_verify` for more details.
          - **update_check:** Bool to Enable/Disable SDK update check and new release notifications.
        """
        # set version and update url from outer scope.
        self.version = version
        """Version string for use once Constructor created."""

        self.update_info_url = update_info_url
        """Update Info URL for use once Constructor Created."""

        # try:
        if controller and isinstance(controller, (binary_type, text_type)):
            self.controller = controller
            self.controller_orig = controller

        if isinstance(ssl_verify, (binary_type, text_type, bool)):
            self.ssl_verify(ssl_verify)

        # handle update check
        if isinstance(update_check, bool):
            self.update_check = update_check

        if update_check:
            self.notify_for_new_version()

        # Create Requests Session.
        self._session = requests.Session()

        # Identify SDK in the User-Agent.
        user_agent = self._session.headers.get('User-Agent')
        if user_agent:
            user_agent += ' (CGX SDK v{0})'.format(self.version)
        else:
            user_agent = 'python-requests/UNKNOWN (CGX SDK v{0})'.format(self.version)

        # Update Headers
        self._session.headers.update({
            'Accept': 'application/json',
            'User-Agent': text_type(user_agent)
        })

        # except Exception as e:
        #     raise ValueError("Unable to create Requests session object: {0}.".format(e))
        api_logger.debug("DEBUG: URL: %s, SSL Verify: %s, Session: %s",
                         self.controller,
                         self.verify,
                         self._session)

        # Bind API method classes to this object
        subclasses = self._subclass_container()
        self.get = subclasses["get"]()
        """API object link to `cloudgenix.get_api.Get`"""

        self.post = subclasses["post"]()
        """API object link to `cloudgenix.post_api.Post`"""

        self.put = subclasses["put"]()
        """API object link to `cloudgenix.put_api.Put`"""

        self.patch = subclasses["patch"]()
        """API object link to `cloudgenix.patch_api.Patch`"""

        self.delete = subclasses["delete"]()
        """API object link to `cloudgenix.delete_api.Delete`"""

        self.interactive = subclasses["interactive"]()
        """API object link to `cloudgenix.interactive.Interactive`"""

        return

    def notify_for_new_version(self):
        """
        Check for a new version of the SDK on API constructor instantiation. If new version found, print
        Notification to STDERR.

        On failure of this check, fail silently.

        **Returns:** No item returned, directly prints notification to `sys.stderr`.
        """

        # broad exception clause, if this fails for any reason just return.
        try:
            recommend_update = False
            update_check_resp = requests.get(self.update_info_url, timeout=3)
            web_version = update_check_resp.json()["info"]["version"]
            api_logger.debug("RETRIEVED_VERSION: %s", web_version)

            available_version = SDK_BUILD_REGEX.search(web_version).groupdict()
            current_version = SDK_BUILD_REGEX.search(self.version).groupdict()

            available_major = available_version.get('major')
            available_minor = available_version.get('minor')
            available_patch = available_version.get('patch')
            available_build = available_version.get('build')
            current_major = current_version.get('major')
            current_minor = current_version.get('minor')
            current_patch = current_version.get('patch')
            current_build = current_version.get('build')

            api_logger.debug("AVAILABLE_VERSION: %s", available_version)
            api_logger.debug("CURRENT_VERSION: %s", current_version)

            # check for major/minor version differences, do not alert for build differences.
            if available_major > current_major:
                recommend_update = True
            elif available_major >= current_major and available_minor > current_minor:
                recommend_update = True
            elif available_major >= current_major and available_minor >= current_minor and \
                    available_patch > current_patch:
                recommend_update = True

            api_logger.debug("NEED_UPDATE: %s", recommend_update)

            # notify.
            if recommend_update:
                sys.stderr.write("WARNING: CloudGenix Python SDK upgrade available. SDKs are typically deprecated 6 "
                                 "months after release of a new version.\n"
                                 "\tLatest Version: {0}\n"
                                 "\tCurrent Version: {1}\n"
                                 "\tFor more info, see 'https://github.com/cloudgenix/sdk-python'. Additionally, this "
                                 "message can be suppressed by instantiating the API with API(update_check=False).\n\n"
                                 "".format(web_version, self.version))

            return

        except Exception:
            # just return and continue.
            return

    def ssl_verify(self, ssl_verify):
        """
        Modify ssl verification settings

        **Parameters:**

          - ssl_verify:
             - True: Verify using builtin BYTE_CA_BUNDLE.
             - False: No SSL Verification.
             - Str: Full path to a x509 PEM CA File or bundle.

        **Returns:** Mutates API object in place, no return.
        """
        self.verify = ssl_verify
        # if verify true/false, set ca_verify_file appropriately
        if isinstance(self.verify, bool):
            if self.verify:  # True
                if os.name == 'nt':
                    # Windows does not allow tmpfile access w/out close. Close file then delete it when done.
                    self._ca_verify_file_handle = temp_ca_bundle(delete=False)
                    self._ca_verify_file_handle.write(BYTE_CA_BUNDLE)
                    self._ca_verify_file_handle.flush()
                    self.ca_verify_filename = self._ca_verify_file_handle.name
                    self._ca_verify_file_handle.close()

                # Other (POSIX/Unix/Linux/OSX)
                else:
                    self._ca_verify_file_handle = temp_ca_bundle()
                    self._ca_verify_file_handle.write(BYTE_CA_BUNDLE)
                    self._ca_verify_file_handle.flush()
                    self.ca_verify_filename = self._ca_verify_file_handle.name

                # register cleanup function for temp file.
                atexit.register(self._cleanup_ca_temp_file)

            else:  # False
                # disable warnings for SSL certs.
                urllib3.disable_warnings()
                self.ca_verify_filename = False
        else:  # Not True/False, assume path to file/dir for Requests
            self.ca_verify_filename = self.verify
        return

    def expose_session(self):
        """
        Call to expose the Requests Session object

        **Returns:** `requests.Session` object
        """
        return self._session

    def add_headers(self, headers):
        """
        Permanently add/overwrite headers to session.

        **Parameters:**

          - **headers:** dict with header/value

        **Returns:** Mutates `requests.Session()` object, no return.
        """
        self._session.headers.update(headers)
        return

    def remove_header(self, header):
        """
        Permanently remove a single header from session

        **Parameters:**

          - **header:** str of single header to remove

        **Returns:** Mutates `requests.Session()` object, no return.
        """
        del self._session.headers[header]
        return

    def set_debug(self, debuglevel):
        """
        Change the debug level of the API

        **Returns:** No item returned.
        """
        if isinstance(debuglevel, int):
            self._debuglevel = debuglevel

        if self._debuglevel == 1:
            logging.basicConfig(level=logging.INFO,
                                format="%(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
            api_logger.setLevel(logging.INFO)
        elif self._debuglevel >= 2:
            logging.basicConfig(level=logging.DEBUG,
                                format="%(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
            requests.cookies.cookielib.debug = True
            api_logger.setLevel(logging.DEBUG)
        else:
            # Remove all handlers
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            # set logging level to default
            requests.cookies.cookielib.debug = False
            api_logger.setLevel(logging.WARNING)

        return

    def _subclass_container(self):
        """
        Call subclasses via function to allow passing parent namespace to subclasses.

        **Returns:** dict with subclass references.
        """
        _parent_class = self

        class GetWrapper(Get):

            def __init__(self):
                self._parent_class = _parent_class

        class PostWrapper(Post):

            def __init__(self):
                self._parent_class = _parent_class

        class PutWrapper(Put):

            def __init__(self):
                self._parent_class = _parent_class

        class PatchWrapper(Patch):

            def __init__(self):
                self._parent_class = _parent_class

        class DeleteWrapper(Delete):

            def __init__(self):
                self._parent_class = _parent_class

        class InteractiveWrapper(Interactive):

            def __init__(self):
                self._parent_class = _parent_class

        return {"get": GetWrapper,
                "post": PostWrapper,
                "put": PutWrapper,
                "patch": PatchWrapper,
                "delete": DeleteWrapper,
                "interactive": InteractiveWrapper}

    def rest_call(self, url, method, data=None, sensitive=False, timeout=None, content_json=True,
                  retry=None, max_retry=None, retry_sleep=None):
        """
        Generic REST call worker function

        **Parameters:**

          - **url:** URL for the REST call
          - **method:** METHOD for the REST call
          - **data:** Optional DATA for the call (for POST/PUT/etc.)
          - **sensitive:** Flag if content request/response should be hidden from logging functions
          - **timeout:** Requests Timeout
          - **content_json:** Bool on whether the Content-Type header should be set to application/json
          - **retry:** Boolean if request should be retried if failure.
          - **max_retry:** Maximum number of retries before giving up
          - **retry_sleep:** Time inbetween retries.

        **Returns:** Requests.Response object, extended with:
          - **cgx_status**: Bool, True if a successful CloudGenix response, False if error.
          - **cgx_content**: Content of the response, guaranteed to be in Dict format. Empty/invalid responses
          will be converted to a Dict response.
        """
        # pull retry related items from Constructor if not specified.
        if timeout is None:
            timeout = self.rest_call_timeout
        if retry is None:
            retry = self.rest_call_retry
        if max_retry is None:
            max_retry = self.rest_call_retry
        if retry_sleep is None:
            retry_sleep = self.rest_call_sleep

        # Retry loop counter
        retry_count = 0

        # Get logging level, use this to bypass logging functions with possible large content if not set.
        logger_level = api_logger.getEffectiveLevel()

        # Run once logic.
        if not retry:
            run_once = True
        else:
            run_once = False

        while retry or run_once:

            # populate headers and cookies from session.
            if content_json and method.lower() not in ['get', 'delete']:
                headers = {
                    'Content-Type': 'application/json'
                }
            else:
                headers = {}

            # add session headers
            headers.update(self._session.headers)
            cookie = self._session.cookies.get_dict()

            # make sure data is populated if present.
            if isinstance(data, (list, dict)):
                data = json.dumps(data)

            api_logger.debug('REST_CALL URL = %s', url)

            # make request
            try:
                if not sensitive:
                    api_logger.debug('\n\tREQUEST: %s %s\n\tHEADERS: %s\n\tCOOKIES: %s\n\tDATA: %s\n',
                                     method.upper(), url, headers, cookie, data)

                # Actual request
                response = self._session.request(method, url, data=data, verify=self.ca_verify_filename,
                                                 stream=True, timeout=timeout, headers=headers, allow_redirects=False)

                # Request complete - lets parse.
                # if it's a non-CGX-good response, don't accept it - wait and retry
                if response.status_code not in [requests.codes.ok,
                                                requests.codes.no_content,
                                                requests.codes.found,
                                                requests.codes.moved]:

                    # Simple JSON debug
                    if not sensitive:
                        try:
                            api_logger.debug('RESPONSE HEADERS: %s\n', json.dumps(
                                json.loads(text_type(response.headers)), indent=4))
                        except ValueError:
                            api_logger.debug('RESPONSE HEADERS: %s\n', text_type(response.headers))
                        try:
                            api_logger.debug('RESPONSE: %s\n', json.dumps(response.json(), indent=4))
                        except ValueError:
                            api_logger.debug('RESPONSE: %s\n', text_type(response.text))
                    else:
                        api_logger.debug('RESPONSE NOT LOGGED (sensitive content)')

                    api_logger.debug("Error, non-200 response received: %s", response.status_code)

                    if retry:
                        # keep retrying
                        retry_count += 1
                        if retry_count >= max_retry:
                            api_logger.info("Max retries of %s reached.", max_retry)
                            retry = False
                        # wait a bit to see if issue clears.
                        sleep(retry_sleep)
                    else:
                        # run once is over.
                        run_once = False
                        # CGX extend requests.Response for return
                        response.cgx_status = False
                        response.cgx_content = self._catch_nonjson_streamresponse(response.text)
                        return response

                else:

                    # Simple JSON debug
                    if not sensitive and (logger_level <= logging.DEBUG and logger_level != logging.NOTSET):
                        try:
                            api_logger.debug('RESPONSE HEADERS: %s\n', json.dumps(
                                json.loads(text_type(response.headers)), indent=4))
                            api_logger.debug('RESPONSE: %s\n', json.dumps(response.json(), indent=4))
                        except ValueError:
                            api_logger.debug('RESPONSE HEADERS: %s\n', text_type(response.headers))
                            api_logger.debug('RESPONSE: %s\n', text_type(response.text))
                    elif sensitive:
                        api_logger.debug('RESPONSE NOT LOGGED (sensitive content)')

                    # if retries have been done, update log if requested.
                    if retry_count > 0:
                        api_logger.debug("Got good response after %s retries.", retry_count)

                    # run once is over, if set.
                    run_once = False
                    # CGX extend requests.Response for return
                    response.cgx_status = True
                    response.cgx_content = self._catch_nonjson_streamresponse(response.text)
                    return response

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:

                api_logger.info("Error, %s.", text_type(e))

                if retry:
                    # keep retrying
                    retry_count += 1
                    if retry_count >= max_retry:
                        api_logger.info("Max retries of %s reached.", max_retry)
                        retry = False
                    # wait a bit to see if issue clears.
                    sleep(retry_sleep)
                else:
                    # run once is over.
                    run_once = False
                    # make a requests.Response object for return since we didn't get one.
                    response = requests.Response

                    # CGX extend requests.Response for return
                    response.cgx_status = False
                    response.cgx_content = {
                        '_error': [
                            {
                                'message': 'REST Request Exception: {}'.format(e),
                                'data': {},
                            }
                        ]
                    }
                    return response

    def _cleanup_ca_temp_file(self):
        """
        Function to clean up ca temp file for requests.

        **Returns:** Removes TEMP ca file, no return
        """
        if os.name == 'nt':
            if isinstance(self.ca_verify_filename, (binary_type, text_type)):
                # windows requires file to be closed for access. Have to manually remove
                os.unlink(self.ca_verify_filename)
        else:
            # other OS's allow close and delete of file.
            self._ca_verify_file_handle.close()

    def parse_auth_token(self, auth_token):
        """
        Break auth_token up into it's constituent values.

        **Parameters:**

          - **auth_token:** Auth_token string

        **Returns:** dict with Auth Token constituents
        """
        # remove the random security key value from the front of the auth_token
        auth_token_cleaned = auth_token.split('-', 1)[1]
        # URL Decode the Auth Token
        auth_token_decoded = self.url_decode(auth_token_cleaned)
        # Create a new dict to hold the response.
        auth_dict = {}

        # Parse the token
        for key_value in auth_token_decoded.split("&"):
            key_value_list = key_value.split("=")
            # check for valid token parts
            if len(key_value_list) == 2 and type(key_value_list[0]) in [text_type, binary_type]:
                auth_dict[key_value_list[0]] = key_value_list[1]

        # Return the dict of key/values in the token.
        return auth_dict

    def update_region_to_controller(self, region):
        """
        Update the controller string with dynamic region info.
        Controller string should end up as `<name[-env]>.<region>.cloudgenix.com`

        **Parameters:**

          - **region:** region string.

        **Returns:** No return value, mutates the controller in the class namespace
        """
        # default region position in a list
        region_position = 1

        # Check for a global "ignore region" flag
        if self.ignore_region:
            # bypass
            api_logger.debug("IGNORE_REGION set, not updating controller region.")
            return

        api_logger.debug("Updating Controller Region")
        api_logger.debug("CONTROLLER = %s", self.controller)
        api_logger.debug("CONTROLLER_ORIG = %s", self.controller_orig)
        api_logger.debug("CONTROLLER_REGION = %s", self.controller_region)

        # Check if this is an initial region use or an update region use
        if self.controller_orig:
            controller_base = self.controller_orig
        else:
            controller_base = self.controller
            self.controller_orig = self.controller

        # splice controller string
        controller_full_part_list = controller_base.split('.')

        for idx, part in enumerate(controller_full_part_list):
            # is the region already in the controller string?
            if region == part:
                # yes, controller already has apropriate region
                api_logger.debug("REGION %s ALREADY IN CONTROLLER AT INDEX = %s", region, idx)
                # update region if it is not already set.
                if self.controller_region != region:
                    self.controller_region = region
                    api_logger.debug("UPDATED_CONTROLLER_REGION = %s", self.controller_region)
                return

        controller_part_count = len(controller_full_part_list)

        # handle short domain case
        if controller_part_count > 1:
            # insert region
            controller_full_part_list[region_position] = region
            self.controller = ".".join(controller_full_part_list)
        else:
            # short domain, just add region
            self.controller = ".".join(controller_full_part_list) + '.' + region

        # update SDK vars with region info
        self.controller_orig = controller_base
        self.controller_region = region

        api_logger.debug("UPDATED_CONTROLLER = %s", self.controller)
        api_logger.debug("UPDATED_CONTROLLER_ORIG = %s", self.controller_orig)
        api_logger.debug("UPDATED_CONTROLLER_REGION = %s", self.controller_region)
        return

    def parse_region(self, login_response):
        """
        Return region from a successful login response.

        **Parameters:**

          - **login_response:** requests.Response from a successful login.

        **Returns:** region name.
        """
        auth_token = login_response.cgx_content['x_auth_token']
        auth_token_dict = self.parse_auth_token(auth_token)
        auth_region = auth_token_dict.get('region')
        return auth_region

    def reparse_login_cookie_after_region_update(self, login_response):
        """
        Sometimes, login cookie gets sent with region info instead of api.cloudgenix.com. This function
        re-parses the original login request and applies cookies to the session if they now match the new region.

        **Parameters:**

          - **login_response:** requests.Response from a non-region login.

        **Returns:** updates API() object directly, no return.
        """

        login_url = login_response.request.url
        api_logger.debug("ORIGINAL REQUEST URL = %s", login_url)
        # replace old controller with new controller.
        login_url_new = login_url.replace(self.controller_orig, self.controller)
        api_logger.debug("UPDATED REQUEST URL = %s", login_url_new)
        # reset login url with new region
        login_response.request.url = login_url_new
        # prep cookie jar parsing
        req = requests.cookies.MockRequest(login_response.request)
        res = requests.cookies.MockResponse(login_response.raw._original_response.msg)
        # extract cookies to session cookie jar.
        self._session.cookies.extract_cookies(res, req)
        return

    @staticmethod
    def _catch_nonjson_streamresponse(rawresponse):
        """
        Validate a streamed response is JSON. Return a Python dictionary either way.


        **Parameters:**

          - **rawresponse:** Streamed Response from Requests.

        **Returns:** Dictionary
        """
        # attempt to load response for return.
        try:
            response = json.loads(rawresponse)
        except (ValueError, TypeError):
            if rawresponse:
                response = {
                    '_error': [
                        {
                            'message': 'Response not in JSON format.',
                            'data': rawresponse,
                        }
                    ]
                }
            else:
                # in case of null response, return empty dict.
                response = {}

        return response

    @staticmethod
    def url_decode(url):
        """
        URL Decode function using REGEX

        **Parameters:**

          - **url:** URLENCODED text string

        **Returns:** Non URLENCODED string
        """
        return re.compile('%([0-9a-fA-F]{2})', re.M).sub(lambda m: chr(int(m.group(1), 16)), url)
