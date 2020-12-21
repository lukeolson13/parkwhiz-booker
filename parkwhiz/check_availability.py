from cached_property import cached_property
import logging
import requests
import sys
import time
import urllib

from datetime import datetime, timedelta

BASE_QUOTES_URL = 'https://api.parkwhiz.com/v4/quotes/'
BASE_BOOKING_URL = 'https://api.parkwhiz.com/v4/bookings/'
DATE_FORMAT = '%Y-%m-%d'
DT_FORMAT = DATE_FORMAT + 'T%H:%M:%S'
LOCATIONS = {
    'COPPER': {
        'location_id': '37193',  # Free Alpine lot
        'q': 'anchor_coordinates:39.50079,-106.154283 search_type:transient bounds:39.50829134860297,'
             '-106.16043976897441,39.50829134860297,-106.13579260107285,39.494053243956756,-106.13579260107285,'
             '39.494053243956756,-106.16043976897441',
    },
}

logger = logging.getLogger(__name__)


class CheckAvailability:
    def __init__(self, location, date, email, license_plate):
        assert location.upper() in LOCATIONS.keys()
        self.location = LOCATIONS[location.upper()]
        self.date = date
        self.email = email
        self.license_plate = license_plate

    @cached_property
    def get_params(self):
        start_dt = (datetime.strptime(self.date, DATE_FORMAT) + timedelta(hours=6)).strftime(DT_FORMAT)
        end_dt = (datetime.strptime(self.date, DATE_FORMAT) + timedelta(hours=22)).strftime(DT_FORMAT)
        returns = 'curated'
        option_types = 'all'
        capabilities = 'capture_plate:always'
        fields = ('quote::default,quote:shuttle_times,location::default,location:timezone,location:site_url,location:'
                  'address2,location:description,location:msa,location:rating_summary')
        
        params = {
            'start_time': start_dt,
            'end_time': end_dt,
            'fields': fields,
            'option_types': option_types,
            'returns': returns,
            'q': self.location['q'],
            'capabilities': capabilities,
        }

        return urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    def _post_params(self, quote_id, final_price=0):
        params = {
            'quote_id': quote_id,
            'plate_number': self.license_plate,
            'final_price': final_price,
            'send_email_confirmation': True,
        }
        params_with_at = {
            'customer_email': self.email,
        }

        params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        params += '&'
        params += urllib.parse.urlencode(params_with_at, quote_via=urllib.parse.quote).replace('%40', '@')

        return params

    def _get(self):
        resp = requests.get(BASE_QUOTES_URL, params=self.get_params)
        data = resp.json()

        return data

    def _post(self, quote_id):
        resp = requests.post(BASE_BOOKING_URL, params=self._post_params(quote_id))
        data = resp.json()
        if isinstance(data, dict) and 'status' in data.keys() and (data['status'] != 200):
            raise ValueError(data['message'])

    def _book(self, quote_id):
        try:
            self._post(quote_id)
            return True
        except Exception as e:
            logger.exception(e)
            print(f'Failure: {e}')
            return False

    def run(self):
        success = False
        fails = 0
        while (not success) and (fails < 5):
            data = self._get()
            if (
                data
                and ('curated_data' in data.keys())
                and (data['curated_data']['cheapest']['location_id'] == self.location['location_id'])
            ):
                quote_id = data['curated_data']['cheapest']['purchase_options'][0]['id']
                success = self._book(quote_id)
                fails += 1
            time.sleep(1)

        if success:
            print('Booked!!!!')
        else:
            raise


if __name__ == '__main__':
    ca = CheckAvailability(sys.argv[1], sys.argv[2])
    ca.run()
