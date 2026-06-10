def calculate_import_cost(
    purchase_price: float = 0,
    shipping_cost: float = 0,
    customs_tax_rate: float = 3.0,
    extra_tax_rate: float = 10.0,
    port_cost: float = 0,
    document_cost: float = 0,
    installation_cost: float = 0,
    other_cost: float = 0,
) -> dict:
    p = float(purchase_price or 0)
    s = float(shipping_cost or 0)
    ctr = float(customs_tax_rate or 0)
    etr = float(extra_tax_rate or 0)
    pc = float(port_cost or 0)
    dc = float(document_cost or 0)
    ic = float(installation_cost or 0)
    oc = float(other_cost or 0)

    sub1 = p + s
    customs = sub1 * ctr / 100
    sub2 = sub1 + customs
    extra = sub2 * etr / 100
    sub3 = sub2 + extra
    total = sub3 + pc + dc + ic + oc

    return {
        "purchase_price": p,
        "shipping_cost": s,
        "sub1": sub1,
        "customs_tax": customs,
        "sub2": sub2,
        "extra_tax": extra,
        "sub3": sub3,
        "port_cost": pc,
        "document_cost": dc,
        "installation_cost": ic,
        "other_cost": oc,
        "total_cost": total,
    }


def calculate_profit(sale_price: float, total_cost: float) -> dict:
    sp = float(sale_price or 0)
    tc = float(total_cost or 0)
    profit = sp - tc
    rate = (profit / sp * 100) if sp > 0 else 0
    margin = (profit / tc * 100) if tc > 0 else 0
    return {
        "sale_price": sp,
        "total_cost": tc,
        "net_profit": profit,
        "profit_rate": rate,
        "margin": margin,
    }


def format_currency(amount: float, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "TRY": "₺", "RMB": "¥"}
    sym = symbols.get(currency, currency)
    return f"{sym}{amount:,.2f}"
