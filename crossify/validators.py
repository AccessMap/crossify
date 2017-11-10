'''Functions for validating and sprucing-up inputs.'''


def validate_sidewalks(sidewalks):
    sidewalks_ls = sidewalks[sidewalks.type == 'LineString']
    n = sidewalks_ls.shape[0]
    if n:
        if n < sidewalks.shape[0]:
            m = sidewalks.shape[0] - n
            print('Warning: Removed {} non-LineString sidewalks'.format(m))
        return sidewalks_ls
    else:
        raise Exception('No LineStrings in sidewalks dataset: are they' +
                        ' MultiLineStrings?')


def validate_streets(streets):
    streets_ls = streets[streets.type == 'LineString']
    n = streets_ls.shape[0]
    if n:
        if n < streets.shape[0]:
            m = streets.shape[0] - n
            print('Warning: Removed {} non-LineString streets'.format(m))
        return streets_ls
    else:
        raise Exception('No LineStrings in streets dataset: are they' +
                        ' MultiLineStrings?')
