# CloudGenix Python SDK v5.0.3b2
Python2 and Python3 SDK for the CloudGenix AppFabric

#### Synopsis
Intended to be a small, lightweight SDK wrapper around the CloudGenix API for easy use. 
Initial version requires knowledge of JSON/Dict objects for POST/PUT/PATCH operations.

#### Requirements
* Active CloudGenix Account
* Python >= 2.7 or >=3.6
* Python modules:
    * Requests + Security Extras >=2.18.4 - <http://docs.python-requests.org/en/master/>

#### Code Example
Comes with `example.py` that shows usage to get a JSON list of sites.

Super-simplified example code (rewrite of example.py in ~4 lines of code):
```python
# Import the CloudGenix SDK API constructor and JSON response pretty printer
from cloudgenix import API, jd

# Instantiate the CloudGenix API constructor
cgx_sess = API()

# Call CloudGenix API login using the Interactive helpers (Handle SAML2.0 login and MSP functions too!).
cgx_sess.interactive.login()

# Print a dump of the list of sites for your selected account
jd(cgx_sess.get.sites())
```

#### License
MIT

#### Version
| Version | Build | Changes |
| ------- | ----- | ------- |
| **5.0.3** | **b2** | Enhanced REST API retry handling and options. |
|           | **b1** | Support for September 2018 Controller release. |
| **5.0.1** | **b1** | Support for July 2018 Controller release, New version notifications, Depreciate legacy _single functions. |
| **4.7.1** | **b1** | Support for May 2018 Controller release. |
| **4.6.1** | **b1** | Support for Mar 2018 Controller release. |
| **4.5.7** | **b1** | Support for Feb 2018 Controller release, Bugfix for issue #4 |
| **4.5.5** | **b4** | Bugfix for certain POST APIs, other minor fixes. |
|           | **b3** | CA Pinning update, *_single function deprecation, add missed 'security' extras requirement. |
|           | **b2** | Various fixes and cleanup for public release. |
|           | **b1** | Update for 15/12/2017 API additions. |
| **4.5.3** | **b2** | Initial Internal Release. |

## For more info
 * Get help and additional CloudGenix Documentation at <http://support.cloudgenix.com>
 * View the autogenerated documentation in the `docs/` directory, or at <https://cloudgenix.github.io/sdk-python/>.
 * View in-python help using `help()` functions. (example: `help(cgx_sess.get.login)`)