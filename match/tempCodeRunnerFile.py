    ranked.sort(key=lambda x: x["total"], reverse=True)
    return [r["portfolio_id"] for r in ranked[:top_k]]