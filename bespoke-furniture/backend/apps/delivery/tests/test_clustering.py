from apps.delivery.services.clustering import GeoPoint, cluster_points, haversine_km, postcode_district


class TestPostcodeDistrict:
    def test_extracts_district_from_full_postcode(self):
        assert postcode_district("S10 2TN") == "S10"
        assert postcode_district("s1 2ab") == "S1"

    def test_falls_back_to_raw_value_when_unparseable(self):
        assert postcode_district("???") == "???"


class TestHaversine:
    def test_same_point_is_zero_distance(self):
        assert haversine_km(53.38, -1.47, 53.38, -1.47) == 0

    def test_known_distance_sheffield_to_london_is_roughly_correct(self):
        # Sheffield city centre to London (approx 227km great-circle distance)
        distance = haversine_km(53.3811, -1.4701, 51.5074, -0.1278)
        assert 215 < distance < 240


class TestClusterPoints:
    def test_empty_input_returns_no_clusters(self):
        assert cluster_points([], target_cluster_count=3) == []

    def test_groups_by_postcode_district_when_target_matches_district_count(self):
        points = [
            GeoPoint(order_id=1, postcode="S10 2TN", latitude=53.38, longitude=-1.50),
            GeoPoint(order_id=2, postcode="S10 3AB", latitude=53.381, longitude=-1.501),
            GeoPoint(order_id=3, postcode="M1 1AE", latitude=53.48, longitude=-2.24),
        ]
        clusters = cluster_points(points, target_cluster_count=2)
        assert len(clusters) == 2
        order_id_sets = [set(c.order_ids) for c in clusters]
        assert {1, 2} in order_id_sets
        assert {3} in order_id_sets

    def test_merges_down_to_a_single_cluster(self):
        points = [
            GeoPoint(order_id=1, postcode="S10 2TN", latitude=53.38, longitude=-1.50),
            GeoPoint(order_id=2, postcode="M1 1AE", latitude=53.48, longitude=-2.24),
            GeoPoint(order_id=3, postcode="LS1 1AA", latitude=53.80, longitude=-1.55),
        ]
        clusters = cluster_points(points, target_cluster_count=1)
        assert len(clusters) == 1
        assert set(clusters[0].order_ids) == {1, 2, 3}

    def test_target_count_never_exceeds_point_count(self):
        points = [GeoPoint(order_id=1, postcode="S10 2TN", latitude=53.38, longitude=-1.50)]
        clusters = cluster_points(points, target_cluster_count=5)
        assert len(clusters) == 1
