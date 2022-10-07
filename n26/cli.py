import click
import n26.n26_api as api
from datetime import datetime, timezone
from n26.utils import create_request_url
from typing import Tuple
from n26.const import (
    AMOUNT,
    CURRENCY,
    REFERENCE_TEXT,
    ATM_WITHDRAW,
    CARD_STATUS_ACTIVE,
    DATETIME_FORMATS,
)

import functools
from tabulate import tabulate
import webbrowser


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
API_CLIENT = api.Api()


def auth_decorator(func: callable):
    """
    Decorator ensuring authentication before making api requests
    :param func: function to patch
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        API_CLIENT.get_refresh_token_from_valid_refresh_token()
        if API_CLIENT.new_auth:
            hint = click.style(
                "Initiating authentication flow, please check your phone to approve login.",
                fg="yellow",
            )
            click.echo(hint)
            API_CLIENT.authenticate()
            success = click.style("Authentication successful :)", fg="green")
            click.echo(success)

        return func(*args, **kwargs)

    return wrapper


# Cli returns command line requests
# with click group i am telling this is the main command
@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-json", default=False, type=bool, is_flag=True
)  # this should be a variable named json
def cli(json: bool):
    """Interact with the https://n26.com API via the command line."""
    print(json)
    global JSON_OUTPUT
    JSON_OUTPUT = json


@cli.command()
@auth_decorator
def info():
    """Get account information"""
    account_info = API_CLIENT.get_account_info()
    if JSON_OUTPUT:
        _print_json(account_info)
        return

    lines = [
        ["Name:", "{} {}".format(account_info.get("firstName"), account_info.get("lastName"))],
        ["Email:", account_info.get("email")],
        ["Gender:", account_info.get("gender")],
        ["Nationality:", account_info.get("nationality")],
        ["Phone:", account_info.get("mobilePhoneNumber")],
    ]

    text = tabulate(lines, [], tablefmt="plain", colalign=["right", "left"])

    click.echo(text)


@cli.command()
@click.option("--categories", default=None, type=str, help="Comma separated list of category IDs.")
@click.option(
    "--pending", default=None, type=bool, help="Whether to show only pending transactions."
)
@click.option(
    "--from",
    "param_from",
    default=None,
    type=click.DateTime(DATETIME_FORMATS),
    help="Start time limit for transactions.",
)
@click.option(
    "--to",
    "param_to",
    default=None,
    type=click.DateTime(DATETIME_FORMATS),
    help="End time limit for transactions.",
)
@click.option("--text-filter", default=None, type=str, help="Text filter.")
@click.option(
    "--limit", default=None, type=click.IntRange(1, 10000), help="Limit transaction output."
)
@auth_decorator
def transactions(
    categories: str,
    pending: bool,
    param_from: datetime or None,
    param_to: datetime or None,
    text_filter: str,
    limit: int,
):
    """Show transactions (default: 5)"""
    if not JSON_OUTPUT and not pending and not param_from and not limit:
        limit = 5
        click.echo(click.style("Output is limited to {} entries.".format(limit), fg="yellow"))

    from_timestamp, to_timestamp = _parse_from_to_timestamps(param_from, param_to)
    transactions_data = API_CLIENT.get_transactions(
        from_time=from_timestamp,
        to_time=to_timestamp,
        limit=limit,
        pending=pending,
        text_filter=text_filter,
        categories=categories,
    )

    if JSON_OUTPUT:
        _print_json(transactions_data)
        return

    lines = []
    for i, transaction in enumerate(transactions_data):
        amount = transaction.get(AMOUNT, 0)
        currency = transaction.get(CURRENCY, None)

        if amount < 0:
            sender_name = "You"
            sender_iban = ""
            recipient_name = transaction.get("merchantName", transaction.get("partnerName", ""))
            recipient_iban = transaction.get("partnerIban", "")
        else:
            sender_name = transaction.get("partnerName", "")
            sender_iban = transaction.get("partnerIban", "")
            recipient_name = "You"
            recipient_iban = ""

        recurring = transaction.get("recurring", "")

        if transaction["type"] == ATM_WITHDRAW:
            message = "ATM Withdrawal"
        else:
            message = transaction.get(REFERENCE_TEXT)

        lines.append(
            [
                _datetime_extractor("visibleTS")(transaction),
                "{} {}".format(amount, currency),
                "{}\n{}".format(sender_name, sender_iban),
                "{}\n{}".format(recipient_name, recipient_iban),
                _insert_newlines(message),
                recurring,
            ]
        )

    headers = ["Date", "Amount", "From", "To", "Message", "Recurring"]
    text = tabulate(lines, headers, numalign="right")

    click.echo(text.strip())


@cli.command()
@auth_decorator
def addresses():
    """ Show account addresses """
    addresses_data = API_CLIENT.get_addresses().get('data')
    if JSON_OUTPUT:
        _print_json(addresses_data)
        return

    headers = ['Type', 'Country', 'City', 'Zip code', 'Street', 'Number',
               'Address line 1', 'Address line 2',
               'Created', 'Updated']
    keys = ['type', 'countryName', 'cityName', 'zipCode', 'streetName', 'houseNumberBlock',
            'addressLine1', 'addressLine2',
            _datetime_extractor('created'), _datetime_extractor('updated')]
    table = _create_table_from_dict(headers, keys, addresses_data, numalign='right')
    click.echo(table)


@cli.command()
@auth_decorator
def balance():
    """Show account balance"""
    balance_data = API_CLIENT.get_balance()
    if JSON_OUTPUT:
        _print_json(balance_data)
        return

    amount = balance_data.get("availableBalance")
    currency = balance_data.get("currency")
    click.echo("{} {}".format(amount, currency))


@cli.command()
def browse():
    """Browse on the web https://app.n26.com/"""
    webbrowser.open("https://app.n26.com/")


def _parse_from_to_timestamps(
    param_from: datetime or None, param_to: datetime or None
) -> Tuple[int, int]:
    """
    Parses cli datetime inputs for "from" and "to" parameters
    :param param_from: "from" input
    :param param_to: "to" input
    :return: timestamps ready to be used by the api
    """
    from_timestamp = None
    to_timestamp = None
    if param_from is not None:
        from_timestamp = int(param_from.timestamp() * 1000) # from ms to s
        if param_to is None:
            # if --from is set, --to must also be set
            param_to = datetime.utcnow()
    if param_to is not None:
        if param_from is None:
            # if --to is set, --from must also be set
            from_timestamp = 1
        to_timestamp = int(param_to.timestamp() * 1000)

    return from_timestamp, to_timestamp


def _print_json(data: dict or list):
    """
    Pretty-Prints the given object to the  console
    :param data: data to print
    """
    import json

    # json.dumps() function converts a Python object into a json string.

    json_data = json.dumps(data, indent=2)
    click.echo(json_data)

def _insert_newlines(text: str, n=40):
    """
    Inserts a newline into the given text every n characters.
    :param text: the text to break
    :param n:
    :return:
    """
    if not text:
        return ""

    lines = []
    for i in range(0, len(text), n):
        lines.append(text[i:i + n])
    return '\n'.join(lines)

def _datetime_extractor(key: str, date_only: bool = False):
    """
    Helper function to extract a datetime value from a dict
    :param key: the dictionary key used to access the value
    :param date_only: removes the time from the output
    :return: an extractor function
    """

    if date_only:
        fmt = "%x"
    else:
        fmt = "%x %X"

    def extractor(dictionary: dict):
        value = dictionary.get(key)
        time = _timestamp_ms_to_date(value)
        if time is None:
            return None
        else:
            time = time.astimezone()
            return time.strftime(fmt)

    return extractor

def _timestamp_ms_to_date(epoch_ms: int) -> datetime or None:
    """
    Convert millisecond timestamp to UTC datetime.
    :param epoch_ms: milliseconds since 1970 in CET
    :return: a UTC datetime object
    """
    if epoch_ms:
        return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc)

if __name__ == "__main__":
    cli()
