"""
Test CSV conversion for portfolio data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.snaptrade import Position, Account, Portfolio


def test_positions_to_csv():
    """Test converting positions to CSV format"""
    positions = [
        Position(symbol="AAPL", quantity=10.5, price=150.25, value=1577.625),
        Position(symbol="GOOGL", quantity=5.0, price=2800.50, value=14002.50),
        Position(symbol="MSFT", quantity=20.0, price=380.75, value=7615.00)
    ]
    
    account = Account(
        id="test_account",
        name="Test Account",
        number="****1234",
        type="Individual",
        institution="Test Broker",
        balance=25000.00,
        positions=positions,
        total_value=23195.125,
        position_count=3
    )
    
    csv_output = account.positions_to_csv()
    print("\n=== Account Positions CSV ===")
    print(csv_output)
    
    # Verify CSV contains expected data
    assert "symbol,quantity,price,value" in csv_output
    assert "AAPL" in csv_output
    assert "GOOGL" in csv_output
    assert "MSFT" in csv_output
    
    print("✅ Positions to CSV test passed!")


def test_portfolio_csv_format():
    """Test converting full portfolio to CSV format"""
    positions1 = [
        Position(symbol="AAPL", quantity=10.0, price=150.00, value=1500.00),
        Position(symbol="TSLA", quantity=5.0, price=700.00, value=3500.00)
    ]
    
    positions2 = [
        Position(symbol="AAPL", quantity=15.0, price=150.00, value=2250.00),
        Position(symbol="GOOGL", quantity=3.0, price=2800.00, value=8400.00)
    ]
    
    account1 = Account(
        id="account1",
        name="Robinhood",
        number="****1111",
        type="Individual",
        institution="Robinhood",
        balance=10000.00,
        positions=positions1,
        total_value=5000.00,
        position_count=2
    )
    
    account2 = Account(
        id="account2",
        name="TD Ameritrade",
        number="****2222",
        type="IRA",
        institution="TD Ameritrade",
        balance=20000.00,
        positions=positions2,
        total_value=10650.00,
        position_count=2
    )
    
    portfolio = Portfolio.from_accounts([account1, account2])
    csv_format = portfolio.to_csv_format()
    
    print("\n=== Portfolio CSV Format ===")
    print(f"Success: {csv_format['success']}")
    print(f"Total Value: ${csv_format['total_value']}")
    print(f"Total Positions: {csv_format['total_positions']}")
    print(f"Account Count: {csv_format['account_count']}")
    
    print("\n--- Aggregated Holdings CSV ---")
    print(csv_format['aggregated_holdings_csv'])
    
    print("\n--- Account Details ---")
    for acc in csv_format['accounts']:
        print(f"\n{acc['name']} ({acc['institution']})")
        print(f"Account Type: {acc['type']}")
        print(f"Total Value: ${acc['total_value']}")
        print(f"Positions CSV:\n{acc['positions_csv']}")
    
    # Verify structure
    assert csv_format['success'] == True
    assert csv_format['total_value'] == 15650.00
    assert csv_format['total_positions'] == 3  # AAPL, TSLA, GOOGL (aggregated)
    assert csv_format['account_count'] == 2
    assert 'aggregated_holdings_csv' in csv_format
    assert len(csv_format['accounts']) == 2
    
    # Verify CSV content
    agg_csv = csv_format['aggregated_holdings_csv']
    assert "AAPL" in agg_csv
    assert "TSLA" in agg_csv
    assert "GOOGL" in agg_csv
    
    # Check that AAPL is aggregated (10 + 15 = 25 shares)
    assert "25.0000" in agg_csv or "25.00" in agg_csv
    
    print("\n✅ Portfolio CSV format test passed!")


def test_csv_size_comparison():
    """Compare size of JSON vs CSV format"""
    import json
    
    # Create a portfolio with many positions
    positions = []
    for i in range(50):
        positions.append(
            Position(
                symbol=f"STOCK{i}",
                quantity=100.5 + i,
                price=50.25 + i,
                value=(100.5 + i) * (50.25 + i)
            )
        )
    
    account = Account(
        id="large_account",
        name="Large Account",
        number="****9999",
        type="Individual",
        institution="Test Broker",
        balance=500000.00,
        positions=positions,
        total_value=sum(p.value for p in positions),
        position_count=len(positions)
    )
    
    portfolio = Portfolio.from_accounts([account])
    
    # Compare sizes
    json_format = portfolio.model_dump()
    csv_format = portfolio.to_csv_format()
    
    json_size = len(json.dumps(json_format))
    csv_size = len(json.dumps(csv_format))
    
    print(f"\n=== Size Comparison (50 positions) ===")
    print(f"JSON format: {json_size:,} bytes")
    print(f"CSV format: {csv_size:,} bytes")
    print(f"Reduction: {json_size - csv_size:,} bytes ({100 * (1 - csv_size/json_size):.1f}% smaller)")
    
    assert csv_size < json_size, "CSV format should be smaller than JSON!"
    
    print("\n✅ CSV size comparison test passed!")


if __name__ == "__main__":
    test_positions_to_csv()
    test_portfolio_csv_format()
    test_csv_size_comparison()
    print("\n🎉 All tests passed!")

