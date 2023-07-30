import csv
import logging
from enum import Enum
from pathlib import Path
from typing import Any

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.accounting.structures.base import HistoryEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry, hash_csv_row
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, AssetMovementCategory, Fee, Location
from rotkehlchen.utils.misc import satoshis_to_btc, ts_sec_to_ms

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitMEXWalletHistoryColnames(Enum):
    transact_time = 'transactTime'
    transact_type = 'transactType'
    amount = 'amount'
    fee = 'fee'
    address = 'address'
    transact_status = 'transactStatus'
    wallet_balance = 'walletBalance'


class BitMEXImporter(BaseExchangeImporter):
    @staticmethod
    def _consume_realised_pnl(
            csv_row: dict[str, Any], timestamp_format: str = '%m/%d/%Y, %H:%M:%S %p',
    ) -> tuple[MarginPosition, HistoryEvent]:
        """
        Use entries resulting from Realised PnL to generate
        MarginPosition an object and HistoryEvent object.
        May raise:
        - KeyError
        - DeserializationError
        """
        close_time = deserialize_timestamp_from_date(
            date=csv_row['transactTime'],
            formatstr=timestamp_format,
            location='Bitmex Wallet History Import',
        )
        realised_pnl = AssetAmount(satoshis_to_btc(deserialize_asset_amount(csv_row['amount'])))
        fee = deserialize_fee(csv_row['fee'])
        notes = f"PnL from trade on {csv_row['address']}"

        log.debug(
            'Processing Bitmex Realised PnL',
            timestamp=close_time,
            profit_loss=realised_pnl,
            fee=fee,
            notes=notes,
        )

        event_identifier = f'BMEX_{hash_csv_row(csv_row)}'
        usd_price = PriceHistorian().query_historical_price(A_BTC, A_USD, close_time)
        abs_amount = realised_pnl.__abs__()  # pylint: disable=no-member
        asset_balance = AssetBalance(A_BTC, Balance(abs_amount, usd_price * abs_amount))
        if realised_pnl < 0:
            history_event_subtype = HistoryEventSubType.SPEND
        else:
            history_event_subtype = HistoryEventSubType.RECEIVE

        margin_position = MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=close_time,
            profit_loss=realised_pnl,
            pl_currency=asset_balance.asset,
            fee=fee,
            fee_currency=asset_balance.asset,
            notes=notes,
            link=f'Imported from BitMEX CSV file. Transact Type: {csv_row["transactType"]}',
        )
        history_event = HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=ts_sec_to_ms(close_time),
            location=Location.BITMEX,
            asset=asset_balance.asset,
            balance=asset_balance.balance,
            notes=notes,
            event_type=HistoryEventType.MARGIN,
            event_subtype=history_event_subtype,
        )

        return margin_position, history_event

    @staticmethod
    def _consume_deposits_or_withdrawals(
            csv_row: dict[str, Any], timestamp_format: str = '%m/%d/%Y, %H:%M:%S %p',
    ) -> AssetMovement:
        asset = A_BTC.resolve_to_asset_with_oracles()
        amount = deserialize_asset_amount_force_positive(csv_row['amount'])
        fee = deserialize_fee(csv_row['fee'])
        transact_type = csv_row['transactType']
        category = AssetMovementCategory.DEPOSIT if transact_type == 'Deposit' else AssetMovementCategory.WITHDRAWAL  # noqa: E501
        amount = AssetAmount(satoshis_to_btc(amount))  # bitmex stores amounts in satoshis
        fee = Fee(satoshis_to_btc(fee))
        ts = deserialize_timestamp_from_date(
            date=csv_row['transactTime'],
            formatstr=timestamp_format,
            location='Bitmex Wallet History Import',
        )
        return AssetMovement(
            location=Location.BITMEX,
            category=category,
            address=deserialize_asset_movement_address(csv_row, 'address', asset),
            transaction_id=get_key_if_has_val(csv_row, 'tx'),
            timestamp=ts,
            asset=asset,
            amount=amount,
            fee_asset=asset,
            fee=fee,
            link=f'Imported from BitMEX CSV file. Transact Type: {transact_type}',
        )

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import deposits, withdrawals and realised pnl events from BitMEX.
        May raise:
        - UnsupportedCSVEntry if operation not supported
        - InputError if a column we need is missing
        """
        history_events = []
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    if row['transactType'] == 'RealisedPNL':
                        margin_position, history_event = self._consume_realised_pnl(row, **kwargs)
                        self.add_margin_trade(cursor, margin_position)
                        history_events.append(history_event)
                    elif row['transactType'] in ['Deposit', 'Withdrawal']:
                        self.add_asset_movement(
                            cursor, self._consume_deposits_or_withdrawals(row, **kwargs),
                        )
                    else:
                        raise UnsupportedCSVEntry(
                            f'transactType {row["transactType"]} is not currently supported',
                        )
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during BitMEX CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
                finally:
                    self.add_history_events(cursor, history_events)  # type: ignore
