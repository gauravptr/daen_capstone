# Class mapping for point cloud annotation

CLASS_NAMES = {
    0: 'seafloor',
    1: 'cube_anomaly',
    2: 'sphere_anomaly',
    3: 'boat_anomaly',
    4: 'coral',
    5: 'rock',
    6: 'wildlife',
    99: 'unknown',
}

MATERIAL_TO_CLASS = {
    '00_seafloor': 0,
    '01_cube_anomaly': 1,
    '02_sphere_anomaly': 2,
    '03_boat_anomaly': 3,
    '04_coral': 4,
    '05_rock': 5,
    '06_wildlife': 6,
    '07_other': 99,
    '99_unknown': 99,
}

ANOMALY_CLASSES = [1, 2, 3]

NORMAL_CLASSES = [0, 4, 5, 6, 99]
