# Class mapping for point cloud annotation

CLASS_NAMES = {
    0: 'seafloor',
    1: 'anomaly',
    2: 'coral',
    3: 'rock',
    4: 'wildlife',
    99: 'unknown',
}

MATERIAL_TO_CLASS = {
    '00_seafloor': 0,
    '01_anomaly': 1,
    '02_coral': 2,
    '03_rock': 3,
    '04_wildlife': 4,
    '99_unknown': 99,
}

ANOMALY_CLASSES = [1, 99]

NORMAL_CLASSES = [0, 2, 3, 4]
