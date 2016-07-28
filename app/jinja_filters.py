def permissions2str(n):
    """Convert permission representation into a string representation.

    Used as a Jinja2 custom filter.
    """
    perms = {0: 'a', 1: 's', 2: 'm', 3: 'u',
             4: 'c', 5: 'w', 6: 'f', 7: 'r'}
    perm_str = "{0:0>8}".format(bin(n).lstrip('0b'))
    result = ''
    for k in perms.keys():
        if perm_str[k] == '1':
            result += perms[k]
        else:
            result += '-'
    return result
    
