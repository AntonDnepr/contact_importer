# -*- coding: utf-8 -*-
""" Live Contact Importer module """
from datetime import date

from .base import BaseProvider
from urllib import urlencode
import requests
import json

AUTH_URL = "https://login.live.com/oauth20_authorize.srf"
TOKEN_URL = "https://login.live.com/oauth20_token.srf"
PERM_SCOPE = "wl.basic,wl.contacts_emails"
CONTACTS_URL = "https://apis.live.net/v5.0/me/contacts?access_token=%s&limit=1000"


class LiveContactImporter(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(LiveContactImporter, self).__init__(*args, **kwargs)
        self.auth_url = AUTH_URL
        self.token_url = TOKEN_URL
        self.perm_scope = PERM_SCOPE

    def request_authorization(self):
        auth_params = {
            "response_type": "code",
            "scope": PERM_SCOPE,
            "redirect_uri": self.redirect_url,
            "client_id": self.client_id
        }

        return "%s?%s" % (self.auth_url, urlencode(auth_params))

    def request_access_token(self, code):
        access_token_params = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_url,
            "grant_type": "authorization_code",
        }

        content_length = len(urlencode(access_token_params))
        access_token_params['content-length'] = str(content_length)

        response = requests.post(self.token_url, data=access_token_params)
        data = json.loads(response.text)
        return data.get('access_token')

    def import_contacts(self, access_token):
        authorization_header = {
            "Authorization": "OAuth %s" % access_token,
            "GData-Version": "3.0"
        }
        response = requests.get(CONTACTS_URL % access_token)
        return self.parse_contacts(response.text)

    def parse_contacts(self, contacts_json):
        contacts_list = json.loads(contacts_json)
        contacts = []
        # c_in is dump of user object
        # (doc addr: http://msdn.microsoft.com/en-us/library/hh243648.aspx#user)
        for c_in in contacts_list['data']:
            contact = {}

            # emails is a dump of wl.emails object
            # (dregionoc addr: http://msdn.microsoft.com/en-us/library/hh243646.aspx#wlemails)
            emails = c_in.pop('emails', {})

            # Set preferred email address
            if emails and 'preferred' in emails and emails['preferred'] and '@' in emails['preferred']:
                contact['email'] = emails['preferred']

            # Provide all existing email fields if they're provided
            if emails:
                # for every type
                for k, v in emails.iteritems():
                    # if v have value and have @ inside
                    if v and '@' in v:
                        # if standard email is not set yet
                        if not contact.get('email'):
                            # set it
                            contact['email'] = v
                        # fill "special" emails
                        contact['%s_email' % k] = v

            # if there are birth_day, birth_month and birth_year and they are not empty
            if 'birth_day' in c_in and c_in['birth_day'] and 'birth_month' in c_in and c_in['birth_month'] \
                    and 'birth_year' in c_in and c_in['birth_year']:
                # create birth date
                contact['birth_date'] = date(
                    year=c_in.pop('birth_year'),
                    month=c_in.pop('birth_month'),
                    day=c_in.pop('birth_day'),
                )

            # addresses is dump of two wl.postaladresses objects "personal" and "business"
            # (docs addrs: http://msdn.microsoft.com/en-us/library/hh243646.aspx#wlpostaladdresses)
            addresses = c_in.pop('addresses', {})

            # If we got any addresses
            if addresses:
                # we will try proccess first business
                business = addresses.pop('business', {})
                # but only if it exist
                # TODO: Change this "if" into extractor function
                if business:
                    # if street exists and have value
                    if 'street' in business and business['street']:
                        # make street
                        contact['addr_street'] = business.pop('street')
                        # if street_2 exists and have value
                        if 'street_2' in business and business['street_2']:
                            # we pack two fields into one universal
                            contact['addr_street'] = "%s\n%s" % (contact['addr_street'], business.pop('street_2'))
                    # TODO: Change it into loop and map
                    # if city exists and have value
                    if 'city' in business and business['city']:
                        # just fill our field by it
                        contact['addr_city'] = business.pop('city')
                    # if state exists and have value
                    if 'state' in business and business['state']:
                        # just fill our field by it
                        contact['addr_state'] = business.pop('state')
                    # if postal_code exists and have value
                    if 'postal_code' in business and business['postal_code']:
                        # just fill our field by it
                        contact['addr_post_code'] = business.pop('postal_code')
                    # if region exists and have value
                    if 'region' in business and business['region']:
                        # just fill our field by it, in interface it's translated to region/country
                        contact['addr_country'] = business.pop('region')

                # we will try proccess personal
                personal = addresses.pop('personal', {})
                # but only if it exist
                # TODO: Change this "if" into extractor function
                if personal:
                    # if street exists and have value
                    if 'street' in personal and personal['street']:
                        # make street
                        contact['addr_private_street'] = personal.pop('street')
                        # if street_2 exists and have value
                        if 'street_2' in personal and personal['street_2']:
                            # we pack two fields into one universal
                            contact['addr_private_street'] = "%s\n%s" % (contact['addr_private_street'], personal.pop('street_2'))
                    # TODO: Change it into loop and map
                    # if city exists and have value
                    if 'city' in personal and personal['city']:
                        # just fill our field by it
                        contact['addr_private_city'] = personal.pop('city')
                    # if state exists and have value
                    if 'state' in personal and personal['state']:
                        # just fill our field by it
                        contact['addr_private_state'] = personal.pop('state')
                    # if postal_code exists and have value
                    if 'postal_code' in personal and personal['postal_code']:
                        # just fill our field by it
                        contact['addr_private_post_code'] = personal.pop('postal_code')
                    # if region exists and have value
                    if 'region' in personal and personal['region']:
                        # just fill our field by it, in interface it's translated to region/country
                        contact['addr_private_country'] = personal.pop('region')

            # phones is dump of wl.phone_numbers object: three strings personal, business, mobile
            # (docs addrs: http://msdn.microsoft.com/en-us/library/hh243646.aspx#wlphone_numbers)
            phones = c_in.pop('phones', {})

            # If we got any phones
            if phones:
                # if personal exists and have value
                if 'personal' in phones and phones['personal']:
                    # just fill our field by it
                    contact['phone_private'] = phones.pop('personal')
                # if business exists and have value
                if 'business' in phones and phones['business']:
                    # just fill our field by it
                    contact['phone'] = phones.pop('business')
                # if personal exists and have value
                if 'mobile' in phones and phones['mobile']:
                    # just fill our field by it
                    contact['phone_mobile'] = phones.pop('mobile')

            contact['name'] = c_in.pop('name', '')
            contact['first_name'] = c_in.pop('first_name', '')
            contact['last_name'] = c_in.pop('last_name', '')
            # New contact have:
            # name, first_name, last_name, email (strings)
            # Can have (you must check if they really exist):
            # preferred_email, account_email, personal_email, business_email (strings)
            # birth_day (datetime.date)
            # addr_street, addr_city, addr_state, addr_post_code, addr_country (strings)
            # addr_private_street, addr_private_city, addr_private_state, (strings)
            # addr_private_post_code, addr_private_country (strings)
            # phone_private, phone, phone_mobile (strings)
            contacts.append(contact)

        return contacts
