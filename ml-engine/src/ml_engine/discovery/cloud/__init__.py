"""Cloud discovery: agents read out of a cloud provider's agent runtime by its list API.

Unlike the endpoint package there is no shared payload format to factor out -- each
provider's list API is its own -- so what a cloud connector shares with the others is
only the record shape, `CloudAgentCreationSource`, which arthur_common already owns.
One package per provider product.
"""
