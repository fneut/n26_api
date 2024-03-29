from logging import raiseExceptions
import requests
from tenacity import retry, stop_after_delay, wait_fixed
from os.path import dirname, abspath

from n26.utils import create_request_url

# from src.customer.colibri.rainflow.n26_project.n26.utils import create_request_url
import time
import yaml
import csv
import os.path

GET = "get"
POST = "post"

EXPIRATION_TIME_KEY = "expiration_time"
ACCESS_TOKEN_KEY = "access_token"
REFRESH_TOKEN_KEY = "refresh_token"
GRANT_TYPE_PASSWORD = "password"
BASE_URL_DE = "https://api.tech26.de"
BASE_URL_GLOBAL = "https://api.tech26.global"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
BASIC_AUTH_HEADERS = {"Authorization": "Basic bmF0aXZld2ViOg=="}
CHALLENGE_TYPE = "oob"
CHALLENGE_TYPE_FOR_MFA = "mfa_oob"
FIELD_NAMES = [REFRESH_TOKEN_KEY, EXPIRATION_TIME_KEY, "time"]


class Api(object):
    def __init__(self, config=None):
        self.token_data = {}
        self.new_auth = False
        self.path = dirname(dirname(abspath(__file__)))
        # self.path = os.path.dirname(__file__)
        if config is None:
            with open(f"{self.path}/credentials.yaml", "r") as stream:
                try:
                    self.config = yaml.safe_load(stream)
                    BASIC_AUTH_HEADERS["device-token"] = self.config["values_token"][
                        "device_token"
                    ]
                except yaml.YAMLError as exc:
                    print(exc)

    def load_refresh_token_from_logs(self):
        try:
            with open(f"{self.path}/refresh_token.csv", "r") as f:
                csv_reader = csv.DictReader(f)
                if REFRESH_TOKEN_KEY in csv_reader.fieldnames:
                    history_of_refresh_token = [line[REFRESH_TOKEN_KEY] for line in csv_reader]
                    self.token_data = {
                        REFRESH_TOKEN_KEY: history_of_refresh_token[-1],
                        }
                    print(f"history_of_refresh_token: {history_of_refresh_token}\n")
                else:
                    raise AssertionError("This should not happen")
        except OSError:
            raise OSError("Not file was found, so setting new_auth to True")

    def save_refresh_token(self):
        """
        saves refresh token in csv
        """
        token_data = self.token_data
        if REFRESH_TOKEN_KEY not in token_data:
            raise ValueError("Refresh token not found in tokens")
        else:
            file_exists = os.path.isfile(f"{self.path}/refresh_token.csv")
            with open(f"{self.path}/refresh_token.csv", "a", newline='') as f:
                csv_writer = csv.DictWriter(f, fieldnames=FIELD_NAMES, delimiter=",")
                if not file_exists:
                    csv_writer.writeheader()
                line_to_write = {
                    REFRESH_TOKEN_KEY: token_data[REFRESH_TOKEN_KEY],
                    EXPIRATION_TIME_KEY: token_data[EXPIRATION_TIME_KEY],
                    "time": time.time(),
                }
                csv_writer.writerow(line_to_write)

    def get_refresh_token_from_valid_refresh_token(self):
        """
        tries to get the refresh token saved in the CSV. If no csv is found,
        then it is a new authentification. With the saved refresh token, an
        access and a new refresh token can be requested
        """
        token_data = self.token_data
        try:
            if REFRESH_TOKEN_KEY not in token_data:
                self.load_refresh_token_from_logs()
            self.new_auth = False
        except AssertionError:
            raise AssertionError("This should not happen")
        except OSError:
            self.new_auth = True

    @property
    def get_device_token(self):
        response = requests.head(f"{BASE_URL_DE}/oauth2/token")
        return response.headers["x-request-id"]

    @property
    def get_mfa_token(self):
        """
        mfaToken is unique token of this login try. If is required for
        the subsequent Authentication requests.
        """
        response = requests.post(
            f"{BASE_URL_GLOBAL}/oauth2/token",
            data=self.config["account"],
            headers={
                **BASIC_AUTH_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if response.status_code != 403:
            raise ValueError(
                "Unexpected response for initial auth request: {}".format(response.text)
            )
        print(response.json(),"\n")
        mfa_token = response.json()["mfaToken"]
        return mfa_token

    def get_notification_in_paired_device(self, mfa_token):
        mfa_data = {
            "mfaToken": mfa_token,
            "challengeType": CHALLENGE_TYPE,
        }
        response = requests.post(
            BASE_URL_DE + "/api/mfa/challenge",
            json=mfa_data,
            headers={
                **BASIC_AUTH_HEADERS,
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            },
        )
        print(response.json(),"\n")
        return response

    @retry(wait=wait_fixed(5), stop=stop_after_delay(60))
    def get_access_and_refresh_token(self, dict_for_login):
        """
        The access token should be used for one session. Validity: 15 mins.
        Should be never stored. The first refresh token has validity of
        90 days, but is one-time usable . With this refresh token,
        an access and a new refresh token can be requested.
        Returns
        -------
            HTTP/1.1 200 OK
            {
                "access_token": "{{access_token}}",
                "token_type": "bearer",
                "refresh_token": "{{refresh_token}}",
                "expires_in": {{expires_in}},
                "scope": "trust",
                "host_url": "{{host_url}}"
            }
        """
        if self.new_auth:
            url_to_query = BASE_URL_DE
        else: 
            url_to_query = BASE_URL_GLOBAL
        print(url_to_query)
        response = requests.post(
            url_to_query + "/oauth2/token",
            data=dict_for_login,
            headers=BASIC_AUTH_HEADERS,
            # headers={
            #     **BASIC_AUTH_HEADERS,
            #     "Content-Type": "application/x-www-form-urlencoded",
            # },
        )
        print(response.json(),"\n")
        if response.status_code == 200:
            tokens = response.json()
            self.token_data = tokens
            response.close()
            return True
        else:
            raise Exception("Waiting for authorisation in paired device")  

    
    def refresh_authenticate(self):
        dict_for_login = {
            "grant_type": REFRESH_TOKEN_KEY,
            REFRESH_TOKEN_KEY: self.token_data[REFRESH_TOKEN_KEY],
        }
        self._get_token(dict_for_login)


    def authenticate(self):
        print("starting new auth process","\n")
        mfa_token = self.get_mfa_token
        print("done with mfa_token","\n")
        self.get_notification_in_paired_device(mfa_token)
        dict_for_login = {
            "mfaToken": mfa_token,
            "grant_type": CHALLENGE_TYPE_FOR_MFA,
        }
        self._get_token(dict_for_login)


    def _get_token(self,data_for_login):
        if not self._validate_token(self.token_data): # no access token or access token expired
            print(f"getting token due to possible expired token, logging into session or new session ({self.new_auth})","\n")
            self.get_access_and_refresh_token(data_for_login)
            self.token_data[EXPIRATION_TIME_KEY] = time.time() + self.token_data["expires_in"]
            print(self.token_data,"\n")
            self.save_refresh_token()
            self.new_auth = False
        else:
            print("no need to reload token (not expired yet)","\n")


    @staticmethod
    def _validate_token(token_data: dict):
        """
        Checks if a token is valid
        :param token_data: the token data to check
        :return: true if valid, false otherwise
        """
        if (ACCESS_TOKEN_KEY not in token_data) or (EXPIRATION_TIME_KEY not in token_data):
            # new_auth = False, but fresh log in, or maybe there was an error adding the expiration time
            return False
        elif time.time() >= token_data[EXPIRATION_TIME_KEY]:
            # token has expired during session
            return False

        return ACCESS_TOKEN_KEY in token_data and token_data[ACCESS_TOKEN_KEY]

    def get_account_info(self) -> dict:
        """
        Retrieves basic user account information
        """
        return self._do_request(GET, BASE_URL_DE + "/api/me")

    def get_account_statuses(self) -> dict:
        """
        Retrieves additional account information
        """
        return self._do_request(GET, BASE_URL_DE + "/api/me/statuses")

    def get_addresses(self) -> dict:
        """
        Retrieves a list of addresses of the account owner
        """
        return self._do_request(GET, BASE_URL_DE + "/api/addresses")

    def get_balance(self) -> dict:
        """
        Retrieves the current balance
        """
        return self._do_request(GET, BASE_URL_DE + "/api/accounts")

    def get_spaces(self) -> dict:
        """
        Retrieves a list of all spaces
        """
        return self._do_request(GET, BASE_URL_DE + "/api/v3/spaces")

    def get_transactions(
        self,
        from_time: int = None,
        to_time: int = None,
        limit: int = 20,
        pending: bool = None,
        categories: str = None,
        text_filter: str = None,
        last_id: str = None,
    ) -> dict:
        """
        Get a list of transactions.
        Note that some parameters can not be combined in a single request (like text_filter and pending) and
        will result in a bad request (400) error.
        :param from_time: earliest transaction time as a Timestamp > 0 - milliseconds since 1970 in CET
        :param to_time: latest transaction time as a Timestamp > 0 - milliseconds since 1970 in CET
        :param limit: Limit the number of transactions to return to the given amount - default 20 as the n26 API returns
        only the last 20 transactions by default
        :param pending: show only pending transactions
        :param categories: Comma separated list of category IDs
        :param text_filter: Query string to search for
        :param last_id: ??
        :return: list of transactions
        """
        if pending and limit:
            # pending does not support limit
            limit = None

        return self._do_request(
            GET,
            BASE_URL_DE + "/api/smrt/transactions",
            {
                "from": from_time,
                "to": to_time,
                "limit": limit,
                "pending": pending,
                "categories": categories,
                "textFilter": text_filter,
                "lastId": last_id,
            },
        )

    def get_statistics(self, from_time: int = 0, to_time: int = int(time.time()) * 1000) -> dict:
        """
        Get statistics in a given time frame
        :param from_time: Timestamp - milliseconds since 1970 in CET
        :param to_time: Timestamp - milliseconds since 1970 in CET
        """

        if not from_time:
            from_time = 0

        if not to_time:
            to_time = int(time.time()) * 1000

        return self._do_request(GET, BASE_URL_DE + '/api/smrt/statistics/categories/%s/%s' % (from_time, to_time))

    def _do_request(
        self,
        method: str = GET,
        url: str = "/",
        params: dict = None,
        json: dict = None,
        headers: dict = None,
    ) -> list or dict or None:
        """
        Executes a http request based on the given parameters
        :param method: the method to use (GET, POST)
        :param url: the url to use
        :param params: query parameters that will be appended to the url
        :param json: request body
        :param headers: custom headers
        :return: the response parsed as a json
        """

        self.refresh_authenticate()
        access_token = self.token_data[ACCESS_TOKEN_KEY]
        _headers = {"Authorization": "Bearer {}".format(access_token)}
        if headers is not None:
            _headers.update(headers)

        url = create_request_url(url, params)

        if method is GET:
            response = requests.get(url, headers=_headers, json=json)
        elif method is POST:
            response = requests.post(url, headers=_headers, json=json)
        else:
            raise ValueError("Unsupported method: {}".format(method))

        response.raise_for_status()
        # some responses do not return data so we just ignore the body in that case
        if len(response.content) > 0:
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            else:
                return response.content


if __name__ == "__main__":
    user_1 = Api()
    user_1.get_refresh_token_from_valid_refresh_token()
    if user_1.new_auth:
        user_1.authenticate()
    else:
        user_1.refresh_authenticate()

    print(user_1.get_transactions())

