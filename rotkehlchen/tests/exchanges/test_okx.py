import warnings as test_warnings
from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_OKX_ASSETS, asset_from_okx
from rotkehlchen.constants.assets import A_ETH, A_SOL, A_USDC, A_USDT
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.okx import Okx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)


def test_name():
    exchange = Okx('okx1', 'a', b'a', 'a', object(), object())
    assert exchange.location == Location.OKX
    assert exchange.name == 'okx1'


def test_assets_are_known(mock_okx: Okx):
    okx_assets = set()
    currencies = mock_okx._api_query('currencies')
    for currency in currencies['data']:
        okx_assets.add(currency['ccy'])

    for okx_asset in okx_assets:
        try:
            asset_from_okx(okx_asset)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in OKX. '
                f'Support for it has to be added',
            ))
        except UnsupportedAsset as e:
            if okx_asset not in UNSUPPORTED_OKX_ASSETS:
                test_warnings.warn(UserWarning(
                    f'Found unsupported asset {e.identifier} in OKX. '
                    f'Support for it has to be added',
                ))


def test_okx_api_signature(mock_okx: Okx):
    sig = mock_okx._generate_signature(
        '2022-12-27T10:55:09.836Z',
        'GET',
        '/api/v5/asset/currencies',
        '',
    )
    assert sig == 'miq5qKL+pRzZJjf0fq0qnUshMuNjvmwHWWyWv0QxsLs='


def test_okx_query_balances(mock_okx: Okx):
    def mock_okx_balances(method, url):     # pylint: disable=unused-argument
        return MockResponse(
            200,
            """
{
   "code":"0",
   "data":[
      {
         "adjEq":"",
         "details":[
            {
               "availBal":"299.9920000068",
               "availEq":"299.9920000068",
               "cashBal":"299.9920000068",
               "ccy":"SOL",
               "crossLiab":"",
               "disEq":"2865.1035952649445",
               "eq":"299.9920000068",
               "eqUsd":"3370.7101120764055",
               "fixedBal":"0",
               "frozenBal":"0",
               "interest":"",
               "isoEq":"0",
               "isoLiab":"",
               "isoUpl":"0",
               "liab":"",
               "maxLoan":"",
               "mgnRatio":"",
               "notionalLever":"0",
               "ordFrozen":"0",
               "spotInUseAmt":"",
               "stgyEq":"0",
               "twap":"0",
               "uTime":"1671542570024",
               "upl":"0",
               "uplLiab":""
            },
            {
               "availBal":"0.027846",
               "availEq":"0.027846",
               "cashBal":"0.027846",
               "ccy":"XMR",
               "crossLiab":"",
               "disEq":"3.260655216",
               "eq":"0.027846",
               "eqUsd":"4.07581902",
               "fixedBal":"0",
               "frozenBal":"0",
               "interest":"",
               "isoEq":"0",
               "isoLiab":"",
               "isoUpl":"0",
               "liab":"",
               "maxLoan":"",
               "mgnRatio":"",
               "notionalLever":"0",
               "ordFrozen":"0",
               "spotInUseAmt":"",
               "stgyEq":"0",
               "twap":"0",
               "uTime":"1666762735059",
               "upl":"0",
               "uplLiab":""
            },
            {
               "availBal":"0.00000065312",
               "availEq":"0.00000065312",
               "cashBal":"0.00000065312",
               "ccy":"USDT",
               "crossLiab":"",
               "disEq":"0.00000065312",
               "eq":"0.00000065312",
               "eqUsd":"0.00000065312",
               "fixedBal":"0",
               "frozenBal":"0",
               "interest":"",
               "isoEq":"0",
               "isoLiab":"",
               "isoUpl":"0",
               "liab":"",
               "maxLoan":"",
               "mgnRatio":"",
               "notionalLever":"0",
               "ordFrozen":"0",
               "spotInUseAmt":"",
               "stgyEq":"0",
               "twap":"0",
               "uTime":"1670953160041",
               "upl":"0",
               "uplLiab":""
            }
         ],
         "imr":"",
         "isoEq":"0",
         "mgnRatio":"",
         "mmr":"",
         "notionalUsd":"",
         "ordFroz":"",
         "totalEq":"3374.785943540432",
         "uTime":"1672123182199"
      }
   ],
   "msg":""
}
            """,
        )

    with patch.object(mock_okx.session, 'request', side_effect=mock_okx_balances):
        balances, msg = mock_okx.query_balances()

    assert msg == ''
    assert balances is not None
    assert len(balances) == 3
    assert (balances[A_XMR.resolve_to_asset_with_oracles()]).amount == FVal('0.027846')
    assert (balances[A_SOL.resolve_to_asset_with_oracles()]).amount == FVal('299.9920000068')
    assert (balances[A_USDT.resolve_to_asset_with_oracles()]).amount == FVal('6.5312E-7')

    warnings = mock_okx.msg_aggregator.consume_warnings()
    errors = mock_okx.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0


def test_okx_query_trades(mock_okx: Okx):
    def mock_okx_trades(method, url):   # pylint: disable=unused-argument
        return MockResponse(
            200,
            """
{
   "code":"0",
   "data":[
      {
         "accFillSz":"30009.966",
         "avgPx":"0.06236",
         "cTime":"1665846604080",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-1.87142147976",
         "feeCcy":"USDT",
         "fillPx":"0.06236",
         "fillSz":"10285.714558",
         "fillTime":"1665846604081",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06236",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"TRX",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"30009.966",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665846604147"
      },
      {
         "accFillSz":"10",
         "avgPx":"0.06174",
         "cTime":"1665641177030",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.01",
         "feeCcy":"TRX",
         "fillPx":"0.06174",
         "fillSz":"10",
         "fillTime":"1665641177031",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06174",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDT",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"10",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665641177086"
      },
      {
         "accFillSz":"24",
         "avgPx":"0.06174",
         "cTime":"1665641133954",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.024",
         "feeCcy":"TRX",
         "fillPx":"0.06174",
         "fillSz":"24",
         "fillTime":"1665641133955",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06174",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDT",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"24",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665641133978"
      },
      {
         "accFillSz":"30000",
         "avgPx":"0.06174",
         "cTime":"1665641100283",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-24",
         "feeCcy":"TRX",
         "fillPx":"0.06174",
         "fillSz":"0.000003",
         "fillTime":"1665641106343",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06174",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDT",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"30000",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665641106388"
      },
      {
         "accFillSz":"3513.8312",
         "avgPx":"1.0001",
         "cTime":"1665594495006",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-3.51418258312",
         "feeCcy":"USDT",
         "fillPx":"1.0001",
         "fillSz":"3513.8312",
         "fillTime":"1665594495008",
         "instId":"USDC-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"market",
         "pnl":"0",
         "posSide":"",
         "px":"",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"3513.8312",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"base_ccy",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665594495121"
      },
      {
         "accFillSz":"4.5",
         "avgPx":"1287.177158951111111",
         "cTime":"1665512880478",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.00315",
         "feeCcy":"ETH",
         "fillPx":"1287.21",
         "fillSz":"2.390191",
         "fillTime":"1665512880479",
         "instId":"ETH-USDC",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"market",
         "pnl":"0",
         "posSide":"",
         "px":"",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"4.5",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"base_ccy",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665512880542"
      },
      {
         "accFillSz":"3600",
         "avgPx":"1",
         "cTime":"1664784938639",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-3.6",
         "feeCcy":"USDT",
         "fillPx":"1",
         "fillSz":"3600",
         "fillTime":"1664784938640",
         "instId":"USDC-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"1",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"3600",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1664784938717"
      },
      {
         "accFillSz":"850",
         "avgPx":"1",
         "cTime":"1664783042522",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.85",
         "feeCcy":"USDT",
         "fillPx":"1",
         "fillSz":"850",
         "fillTime":"1664783042523",
         "instId":"USDC-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"555555555555555555",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"1",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"850",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1664783042604"
      }
   ],
   "msg":""
}""",
        )

    with patch.object(mock_okx.session, 'request', side_effect=mock_okx_trades):
        trades = mock_okx.query_online_trade_history(Timestamp(1609103082), Timestamp(1672175105))

    expected_trades = ([
        Trade(
            timestamp=Timestamp(1665846604),
            location=Location.OKX,
            base_asset=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal(30009.966)),
            rate=Price(FVal(0.06236)),
            fee=Fee(FVal(1.87142147976)),
            fee_currency=A_USDT,
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1665641177),
            location=Location.OKX,
            base_asset=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(10)),
            rate=Price(FVal(0.06174)),
            fee=Fee(FVal(0.01)),
            fee_currency=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1665641133),
            location=Location.OKX,
            base_asset=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(24)),
            rate=Price(FVal(0.06174)),
            fee=Fee(FVal(0.024)),
            fee_currency=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1665641100),
            location=Location.OKX,
            base_asset=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(30000)),
            rate=Price(FVal(0.06174)),
            fee=Fee(FVal(24)),
            fee_currency=Asset('eip155:1/erc20:0xf230b790E05390FC8295F4d3F60332c93BEd42e2'),
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1665594495),
            location=Location.OKX,
            base_asset=A_USDC,
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal(3513.8312)),
            rate=Price(FVal(1.0001)),
            fee=Fee(FVal(3.51418258312)),
            fee_currency=A_USDT,
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1665512880),
            location=Location.OKX,
            base_asset=A_ETH,
            quote_asset=A_USDC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(4.5)),
            rate=Price(FVal('1287.177158951111111')),
            fee=Fee(FVal(0.00315)),
            fee_currency=A_ETH,
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1664784938),
            location=Location.OKX,
            base_asset=A_USDC,
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal(3600)),
            rate=Price(FVal(1)),
            fee=Fee(FVal(3.6)),
            fee_currency=A_USDT,
            link='555555555555555555',
            notes=None,
        ),
        Trade(
            timestamp=Timestamp(1664783042),
            location=Location.OKX,
            base_asset=A_USDC,
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal(850)),
            rate=Price(FVal(1)),
            fee=Fee(FVal(0.85)),
            fee_currency=A_USDT,
            link='555555555555555555',
            notes=None,
        ),
    ], (1609103082, 1672175105))

    assert trades == expected_trades


def test_okx_query_deposits_withdrawals(mock_okx: Okx):
    def mock_okx_deposits_withdrawals(method, url):     # pylint: disable=unused-argument
        if 'deposit' in url:
            data = """
{
   "code":"0",
   "data":[
      {
         "actualDepBlkConfirm":"991",
         "amt":"2500.180327",
         "areaCodeFrom":"",
         "ccy":"USDT",
         "chain":"USDT-Arbitrum one",
         "depId":"88888888",
         "from":"",
         "fromWdId":"",
         "state":"2",
         "to":"0xaab27b150451726ec7738aa1d0a94505c8729bd1",
         "ts":"1669963555000",
         "txId":"0xfd12f8850218dc9d1d706c2dbd6c38f495988109c220bf8833255697b85c92db"
      },
      {
         "actualDepBlkConfirm":"200",
         "amt":"990.795352",
         "areaCodeFrom":"",
         "ccy":"USDC",
         "chain":"USDC-Polygon",
         "depId":"88888888",
         "from":"",
         "fromWdId":"",
         "state":"2",
         "to":"0xaab27b150451726ec7738aa1d0a94505c8729bd1",
         "ts":"1669405596000",
         "txId":"0xcea993d53b2c1f79430a003fb8facb5cd6b83b6cb6a502b6233d83eb338ba8ba"
      }
   ],
   "msg":""
}
            """
        elif 'withdraw' in url:
            data = """
{
   "code":"0",
   "data":[
      {
         "chain":"SOL-Solana",
         "areaCodeFrom":"",
         "clientId":"",
         "fee":"0.008",
         "amt":"49.86051649",
         "txId":"46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPXBryVuH6qJmQysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU",
         "areaCodeTo":"",
         "ccy":"SOL",
         "from":"",
         "to":"9ZLfHwxzgbZi3eiK43duZVJ2nXft3mtkRMjs9YD5Yds2",
         "state":"2",
         "nonTradableAsset":false,
         "ts":"1671542569000",
         "wdId":"66666666",
         "feeCcy":"SOL"
      },
      {
         "chain":"USDT-Arbitrum one",
         "areaCodeFrom":"",
         "clientId":"",
         "fee":"0.1",
         "amt":"421.169831",
         "txId":"0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f",
         "areaCodeTo":"",
         "ccy":"USDT",
         "from":"",
         "to":"0x388c818ca8b9251b393131c08a736a67ccb19297",
         "state":"2",
         "nonTradableAsset":false,
         "ts":"1670953159000",
         "wdId":"66666666",
         "feeCcy":"USDT"
      }
   ],
   "msg":""
}
            """
        else:
            data = ''
        return MockResponse(200, data)

    with patch.object(
            mock_okx.session,
            'request',
            side_effect=mock_okx_deposits_withdrawals,
    ):
        asset_movements = mock_okx.query_online_deposits_withdrawals(
            Timestamp(1609103082),
            Timestamp(1672175105),
        )

    expected_asset_movements = [
        AssetMovement(
            location=Location.OKX,
            category=AssetMovementCategory.DEPOSIT,
            timestamp=Timestamp(1669963555),
            address='0xAAB27b150451726EC7738aa1d0A94505c8729bd1',
            transaction_id='0xfd12f8850218dc9d1d706c2dbd6c38f495988109c220bf8833255697b85c92db',
            asset=A_USDT,
            amount=FVal(2500.180327),
            fee_asset=A_USDT,
            fee=Fee(FVal(0)),
            link='0xfd12f8850218dc9d1d706c2dbd6c38f495988109c220bf8833255697b85c92db',
        ),
        AssetMovement(
            location=Location.OKX,
            category=AssetMovementCategory.DEPOSIT,
            timestamp=Timestamp(1669405596),
            address='0xAAB27b150451726EC7738aa1d0A94505c8729bd1',
            transaction_id='0xcea993d53b2c1f79430a003fb8facb5cd6b83b6cb6a502b6233d83eb338ba8ba',
            asset=A_USDC,
            amount=FVal(990.795352),
            fee_asset=A_USDC,
            fee=Fee(FVal(0)),
            link='0xcea993d53b2c1f79430a003fb8facb5cd6b83b6cb6a502b6233d83eb338ba8ba',
        ),
        AssetMovement(
            location=Location.OKX,
            category=AssetMovementCategory.WITHDRAWAL,
            timestamp=Timestamp(1671542569),
            address='9ZLfHwxzgbZi3eiK43duZVJ2nXft3mtkRMjs9YD5Yds2',
            transaction_id='46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPX'
                           'BryVuH6qJmQysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU',
            asset=A_SOL,
            amount=FVal(49.86051649),
            fee_asset=A_SOL,
            fee=Fee(FVal(0.008)),
            link='46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPXBryVuH6qJm'
                 'Qysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU',
        ),
        AssetMovement(
            location=Location.OKX,
            category=AssetMovementCategory.WITHDRAWAL,
            timestamp=Timestamp(1670953159),
            address='0x388C818CA8B9251b393131C08a736A67ccB19297',
            transaction_id='0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f',
            asset=A_USDT,
            amount=FVal(421.169831),
            fee_asset=A_USDT,
            fee=Fee(FVal(0.1)),
            link='0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f'),
    ]

    assert asset_movements == expected_asset_movements
