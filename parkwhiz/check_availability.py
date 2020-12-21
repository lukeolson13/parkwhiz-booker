from cached_property import cached_property
import requests
import sys
import urllib

from datetime import datetime, timedelta

BASE_URL = 'https://api.parkwhiz.com/v4/quotes/'
DATE_FORMAT = '%Y-%m-%d'
DT_FORMAT = DATE_FORMAT + 'T%H:%M:%S'
LOCATIONS = {
    'COPPER': {
        'location_id': '37193',
        'q': 'anchor_coordinates:39.50079,-106.154283 search_type:transient bounds:39.50829134860297,'
             '-106.16043976897441,39.50829134860297,-106.13579260107285,39.494053243956756,-106.13579260107285,'
             '39.494053243956756,-106.16043976897441',
    },
}


class CheckAvailability:
    def __init__(self, location, date):
        assert location.upper() in LOCATIONS.keys()
        self.location = LOCATIONS[location.upper()]
        self.date = date


    @cached_property
    def request_params(self):
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

    def _get(self):
        resp = requests.get(BASE_URL, params=self.request_params)
        data = resp.json()

        return data

    def run(self):
        data = self._get()
        if (
            data
            and ('curated_data' in data.keys())
            and (data['curated_data']['cheapest']['location_id'] == self.location['location_id'])
        ):
            print('available!')
        else:
            print('no no no...')


if __name__ == '__main__':
    ca = CheckAvailability(sys.argv[1], sys.argv[2])
    ca.run()
