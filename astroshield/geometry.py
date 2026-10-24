"""Geometría esférica básica.

Todas las posiciones se expresan como (latitud, longitud) en grados sobre un
modelo esférico de la Tierra. Internamente se usan vectores unitarios, lo que
evita problemas en los polos y en el antimeridiano (±180°).
"""
import math

R_EARTH_KM = 6371.0


def to_vec(lat, lon):
    """(lat, lon) en grados -> vector unitario (x, y, z)."""
    la, lo = math.radians(lat), math.radians(lon)
    c = math.cos(la)
    return (c * math.cos(lo), c * math.sin(lo), math.sin(la))


def to_latlon(v):
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z)
    return (math.degrees(math.asin(max(-1.0, min(1.0, z / n)))),
            math.degrees(math.atan2(y, x)))


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def ang_dist_vec(a, b):
    """Distancia angular (grados) entre dos vectores unitarios."""
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(a, b)))))


def ang_dist(lat1, lon1, lat2, lon2):
    """Distancia angular (grados) del gran círculo entre dos puntos."""
    return ang_dist_vec(to_vec(lat1, lon1), to_vec(lat2, lon2))


def km_to_deg(km):
    return math.degrees(km / R_EARTH_KM)


def deg_to_km(deg):
    return math.radians(deg) * R_EARTH_KM


def bearing(lat1, lon1, lat2, lon2):
    """Rumbo inicial (grados) desde el punto 1 hacia el punto 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x))


def destination(lat, lon, bearing_deg, dist_deg):
    """Punto alcanzado al recorrer dist_deg grados con rumbo bearing_deg."""
    p1, l1 = math.radians(lat), math.radians(lon)
    b, d = math.radians(bearing_deg), math.radians(dist_deg)
    p2 = math.asin(max(-1.0, min(1.0,
        math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1),
                         math.cos(d) - math.sin(p1) * math.sin(p2))
    lon2 = (math.degrees(l2) + 540.0) % 360.0 - 180.0
    return (math.degrees(p2), lon2)


def footprint_half_angle(alt_km, min_elev_deg):
    """Semiángulo (grados, centro de la Tierra) del área que ve un satélite.

    Un punto del suelo es visible si el satélite aparece al menos min_elev_deg
    sobre su horizonte:  lambda = arccos(R cos(e) / (R + h)) - e
    """
    e = math.radians(min_elev_deg)
    lam = math.acos(R_EARTH_KM * math.cos(e) / (R_EARTH_KM + alt_km)) - e
    return math.degrees(lam)


def random_point(rng):
    """Punto uniforme en área sobre la esfera (no se concentra en los polos)."""
    lat = math.degrees(math.asin(2.0 * rng.random() - 1.0))
    lon = rng.uniform(-180.0, 180.0)
    return (lat, lon)


def disk_samples(lat, lon, radius_deg, n):
    """n puntos repartidos uniformemente en un disco esférico (espiral de Vogel)."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    pts = []
    for i in range(n):
        r = radius_deg * math.sqrt((i + 0.5) / n)
        pts.append(destination(lat, lon, math.degrees(i * golden), r))
    return pts
