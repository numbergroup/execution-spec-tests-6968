"""
Test EIP-6968: Contract Secured Revenue
EIP: https://eips.ethereum.org/EIPS/eip-6968
"""

import pytest

from typing import Mapping
from ethereum_test_tools import (
    AddrAA,
    AddrBB,
    Account,
    Environment,
    Opcodes as Op,
    StateTestFiller,
    TestAddress,
    Transaction,
    to_address,
)

from ethereum_test_tools.common.conversions import to_number

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-6968.md"
REFERENCE_SPEC_VERSION = "7500ac4fc1bbdfaf684e7ef851f798f6b667b2fe"

REVENUE_SHARE_QUOTIENT = 5


def calc_revenue(base_fee: int, gas_used: int) -> int:
    """
    calc_revenue returns the revenue expected to be earned by the contract
    given a specific base fee and gas used value.
    """
    return gas_used * base_fee // REVENUE_SHARE_QUOTIENT


@pytest.mark.valid_from("Prague")
def test_simple_tx(state_test: StateTestFiller):
    """
    Test that EOA to EOA transfer behavior does not change.
    """
    env = Environment()
    balance = 1000000000000000000000

    pre = {
        TestAddress: Account(balance=balance),
        AddrAA: Account(balance=100),
    }
    tx = Transaction(
        to=to_address("0xaa"),
        gas_price=10,
    )
    post = {
        TestAddress: Account(balance=balance - 10 * 21000),
        AddrAA: Account(balance=100),
    }

    state_test(env=env, pre=pre, post=post, txs=[tx])


class TestCase:
    """
    TestCase represents a single EIP-6968 test case.
    """

    __test__ = False

    def __init__(self, name, accounts, gas_limit=100000):
        self.name = name
        self.accounts = accounts
        self.gas_limit = gas_limit + 21000  # add 21,000 for intrinsic gas


single_frame_tests = [
    TestCase(
        name="simply add two numbers",
        accounts={
            AddrAA: {
                "code": (Op.ADD(Op.PUSH1(0x01), Op.PUSH1(0x41))),
                "gas_used": 9,
            }
        },
    ),
    TestCase(
        name="read env values",
        accounts={
            AddrAA: {
                "code": (Op.BASEFEE + Op.ORIGIN + Op.SELFBALANCE + Op.CALLVALUE),
                "gas_used": 11,
            }
        },
    ),
    TestCase(
        name="out-of-gas",
        accounts={AddrAA: {"code": (Op.SELFBALANCE), "gas_used": 4}},
        gas_limit=4,
    ),
    TestCase(
        name="simple call",
        accounts={
            AddrAA: {
                "code": Op.CALL(
                    Op.GAS,
                    Op.PUSH20(AddrBB),
                    0,
                    0,
                    0,
                    0,
                    0,
                ),
                "gas_used": 2600 + 6 * 3 + 2,
            },
            AddrBB: {
                "code": Op.SELFBALANCE,
                "gas_used": 5,
            },
        },
    ),
]


@pytest.mark.parametrize(
    "accounts,gas_limit",
    [(t.accounts, t.gas_limit) for t in single_frame_tests],
    ids=[t.name for t in single_frame_tests],
)
@pytest.mark.valid_from("Prague")
def test_execution(
    state_test: StateTestFiller,
    env: Environment,
    pre: Mapping[str, Account],
    post: Mapping[str, Account],
    tx: Transaction,
):
    """
    Test that revenue is calculated correctly in a single frame of execution.
    """
    state_test(env=env, pre=pre, post=post, txs=[tx])


@pytest.fixture
def env() -> Environment:  # noqa: D103
    return Environment(base_fee=7)


@pytest.fixture
def pre(accounts: Mapping) -> Mapping:  # noqa: D103
    out = {
        TestAddress: Account(balance=10**40),
    }
    for addr, account in accounts.items():
        out[addr] = Account(code=account["code"])

    return out


@pytest.fixture
def post(env: Environment, accounts: Mapping) -> Mapping:  # noqa: D103
    assert env.base_fee is not None
    out = {}
    for addr, account in accounts.items():
        out[addr] = Account(balance=calc_revenue(to_number(env.base_fee), account["gas_used"]))
    return out


@pytest.fixture
def tx(gas_limit) -> Transaction:  # noqa: D103
    return Transaction(
        to=AddrAA,
        gas_limit=gas_limit,
    )
