import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_SAI
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.poloniex import trade_from_poloniex
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Fee, Location, Price, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SAI_TIMESTAMP = 1574035200


class PoloniexTradesImporter(BaseExchangeImporter):

    def _consume_poloniex_trade(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = 'iso8601',
    ) -> None:
        """
        Consume the file containing only trades from ShapeShift.
        May raise:
        - DeserializationError if failed to deserialize timestamp or amount
        - UnknownAsset if unknown asset in the csv row was found
        - KeyError if csv_row does not have expected cells
        """
        trade = trade_from_poloniex(csv_row)
        self.add_trade(write_cursor, trade)

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_poloniex_trade(write_cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During Poloniex CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Poloniex CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
