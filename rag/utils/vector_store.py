def vector_map(raw):
    if isinstance(raw, dict):
        out = {}
        for key, value in raw.items():
            if not isinstance(value, list) or not value:
                continue
            try:
                out[int(key)] = value
            except (TypeError, ValueError):
                continue
        return out
    if isinstance(raw, list) and raw:
        return {len(raw): raw}
    return {}


def vector_for_dim(raw, dim):
    if not dim:
        return None
    return vector_map(raw).get(int(dim))


def packed_vector(values, existing=None):
    data = vector_map(existing)
    values = list(values or [])
    if values:
        data[len(values)] = values
    return {str(key): value for key, value in data.items()}
