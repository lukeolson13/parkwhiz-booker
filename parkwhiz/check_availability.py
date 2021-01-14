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
        'location_id': '37193',  # Alpine lot (free)
        'q': 'anchor_coordinates:39.50079,-106.154283 search_type:transient bounds:39.50829134860297,'
             '-106.16043976897441,39.50829134860297,-106.13579260107285,39.494053243956756,-106.13579260107285,'
             '39.494053243956756,-106.16043976897441',
        'start_hour': 6,
        'end_hour': 22,
    },
    'ELDORA': {
        'location_id': '37234',  # Main lot (free)
        'q': 'anchor_coordinates:39.937239,-105.582921 search_type:transient bounds:39.957239,'
             '-105.602921,39.917238999999995,-105.562921 event_id:1075385',
        'start_hour': 8,
        'end_hour': 16,
    }
}

logger = logging.getLogger(__name__)


class CheckAvailability:
    def __init__(self, location, date, email, license_plate):
        assert location.upper() in LOCATIONS.keys()
        self.location = location
        self.location_meta = LOCATIONS[self.location.upper()]
        self.date = date
        self.email = email
        self.license_plate = license_plate

    @cached_property
    def get_params(self):
        start_dt = (datetime.strptime(self.date, DATE_FORMAT)
                    + timedelta(hours=self.location_meta['start_hour'])).strftime(DT_FORMAT)
        end_dt = (datetime.strptime(self.date, DATE_FORMAT)
                  + timedelta(hours=self.location_meta['end_hour'])).strftime(DT_FORMAT)
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
            'q': self.location_meta['q'],
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
                and (data['curated_data']['cheapest']['location_id'] == self.location_meta['location_id'])
            ):
                cheapest_option = data['curated_data']['cheapest']['purchase_options'][0]
                price = float(cheapest_option['price']['USD'])
                if price != 0.0:
                    raise ValueError("WTF! {location}'s lot ({location_id}) is no longer free. It's ${price}".format(
                        location=self.location, location_id=self.location_meta['location_id'], price=price,
                    ))
                quote_id = cheapest_option['id']
                success = self._book(quote_id)
                fails += 1
            time.sleep(1)

        if success:
            print('Booked!!!!')
        else:
            raise


if __name__ == '__main__':
    ca = CheckAvailability(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    ca.run()
