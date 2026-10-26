"""Network discovery: internal sources seen calling hosts that serve model inference.

A network log -- a DNS query log, a flow log, a proxy or firewall log -- names a source
and a destination per line. What every network source shares is lifted out here: the
configurable extractor that pulls the two from a line (`extractor`), the destinations
that count as inference (`hosts`), and folding the matches into one record per source
(`records`). Each vendor package holds only how its log lines are read. One package per
vendor product.
"""
