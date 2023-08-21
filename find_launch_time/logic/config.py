geofabrik_osm_column_types = {
    'name': 'category',
    'highway': 'category',
    'waterway': 'category',
    'aerialway': 'category',
    'barrier': 'category',
    'man_made': 'category',
    'table_name': 'category',
    'type': 'category',
    'aeroway': 'category',
    'amenity': 'category',
    'admin_level': 'category',
    'boundary': 'category',
    'building': 'category',
    'craft': 'category',
    'geological': 'category',
    'historic': 'category',
    'land_area': 'category',
    'landuse': 'category',
    'leisure': 'category',
    'military': 'category',
    'natural': 'category',
    'office': 'category',
    'place': 'category',
    'shop': 'category',
    'sport': 'category',
    'tourism': 'category',
}

all_element_types = ['node', 'way', 'relation', 'area']

bad_landing_tags = [
    ('landuse', 'residential'),
    ('landuse', 'commercial'),
    ('landuse', 'industrial'),
    ('landuse', 'retail'),
    ('landuse', 'institutional'),
    ('landuse', 'education'),
    ('landuse', 'civil'),
    ('place', 'city_block'),
    ('building', '*'),
    ('natural', 'water'),
]


human_crs = 'EPSG:4326'
processing_crs = 'EPSG:3857'

small_patch_of_Helsinki = (24.904289,60.178148,24.957504,60.194364)
bbox = small_patch_of_Helsinki

max_bad_landing_proportion = 0.15
