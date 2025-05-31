import copy

import factory

from customfit.userauth.factories import UserFactory

from .models import Body, Grade, GradeSet, MeasurementSet


class MeasurementSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeasurementSet

    waist_circ = 32
    bust_circ = 41
    upper_torso_circ = 38
    wrist_circ = 6
    forearm_circ = 10
    bicep_circ = 12
    elbow_circ = 10
    armpit_to_short_sleeve = 1
    armpit_to_elbow_sleeve = 6
    armpit_to_three_quarter_sleeve = 12
    armpit_to_full_sleeve = 17.5
    inter_nipple_distance = 8
    armpit_to_waist = 9
    armhole_depth = 8
    armpit_to_high_hip = 14.5
    high_hip_circ = 37
    armpit_to_med_hip = 16
    med_hip_circ = 40
    armpit_to_low_hip = 18
    low_hip_circ = 42
    armpit_to_tunic = 24
    tunic_circ = 44
    cross_chest_distance = None


# Note: see get_csv_body, below, if you want to access a variety of 'real' bodies
class BodyFactory(MeasurementSetFactory):

    class Meta:
        model = Body
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ("name",)

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: "factory-built body %s" % n)
    notes = ""
    archived = False
    body_type = Body.BODY_TYPE_ADULT_WOMAN
    featured_pic = None


class SimpleBodyFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Body
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ("name",)

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: "factory-built simple body %s" % n)
    notes = ""
    archived = False
    waist_circ = 32
    bust_circ = 41
    upper_torso_circ = None
    wrist_circ = 6
    forearm_circ = None
    bicep_circ = 12
    elbow_circ = None
    armpit_to_short_sleeve = None
    armpit_to_elbow_sleeve = None
    armpit_to_three_quarter_sleeve = None
    armpit_to_full_sleeve = 17.5
    inter_nipple_distance = None
    armpit_to_waist = None
    armhole_depth = 8
    armpit_to_high_hip = None
    high_hip_circ = None
    armpit_to_med_hip = 16
    med_hip_circ = 40
    armpit_to_low_hip = None
    low_hip_circ = None
    armpit_to_tunic = None
    tunic_circ = None
    cross_chest_distance = None
    body_type = Body.BODY_TYPE_UNSTATED
    featured_pic = None


class FemaleBodyFactory(BodyFactory):
    name = factory.Sequence(lambda n: "factory-built woman's body %s" % n)
    body_type = Body.BODY_TYPE_ADULT_WOMAN


class MaleBodyFactory(SimpleBodyFactory):
    body_type = Body.BODY_TYPE_ADULT_MAN
    name = factory.Sequence(lambda n: "factory-built man's body %s" % n)


class ChildBodyFactory(SimpleBodyFactory):
    body_type = Body.BODY_TYPE_CHILD
    name = factory.Sequence(lambda n: "factory-built child's body %s" % n)


class UnstatedTypeBodyFactory(SimpleBodyFactory):
    body_type = Body.BODY_TYPE_UNSTATED
    name = factory.Sequence(lambda n: "factory-built unstated-type body %s" % n)


# Hard-coded bodies needed for tests. Note: called 'csv' bodies for historical
# reasons. (They used to be stored in CSV format.) We keep them around becuase
# (1) they are used in some regression tests, and (2) it's useful to have a set of
# real body-measurements around to make sure that our engine can handle them
# To access them, you *can* get a copy of the dict through `csv_bodies`, but we
# suggest that you get them through `get_csv_body` (which will use BodyFactory)
# to give you a real Body instance instead of a dict).

csv_bodies = {
    "Test 1": {
        "armpit_to_elbow_sleeve": 6.0,
        "armpit_to_full_sleeve": 17.5,
        "armpit_to_short_sleeve": 1.0,
        "armpit_to_three_quarter_sleeve": 12.0,
        "bicep_circ": 12.0,
        "bust_circ": 41.0,
        "elbow_circ": 10.0,
        "forearm_circ": 10.0,
        "high_hip_circ": 37.0,
        "inter_nipple_distance": 8.0,
        "low_hip_circ": 40.0,
        "med_hip_circ": 40.0,
        "name": "Test 1",
        "tunic_circ": 43.0,
        "upper_torso_circ": 38.0,
        "waist_circ": 32.0,
        "armpit_to_waist": 9.0,
        "armpit_to_high_hip": 14.0,
        "armpit_to_low_hip": 18.0,
        "armpit_to_med_hip": 16.0,
        "armhole_depth": 8.0,
        "armpit_to_tunic": 22.0,
        "wrist_circ": 6.0,
    },
    "Test 2": {
        "armpit_to_elbow_sleeve": 6.0,
        "armpit_to_full_sleeve": 17.0,
        "armpit_to_short_sleeve": 2.0,
        "armpit_to_three_quarter_sleeve": 12.0,
        "bicep_circ": 10.0,
        "bust_circ": 32.0,
        "elbow_circ": 9.0,
        "forearm_circ": 8.0,
        "high_hip_circ": 33.0,
        "inter_nipple_distance": 7.0,
        "low_hip_circ": 36.5,
        "med_hip_circ": 35.0,
        "name": "Test 2",
        "tunic_circ": 38.0,
        "upper_torso_circ": 33.0,
        "waist_circ": 29.0,
        "armpit_to_waist": 8.0,
        "armpit_to_high_hip": 14.0,
        "armpit_to_low_hip": 19.0,
        "armpit_to_med_hip": 17.0,
        "armhole_depth": 7.5,
        "armpit_to_tunic": 21.0,
        "wrist_circ": 6.0,
    },
    "Test 3": {
        "armpit_to_elbow_sleeve": 8.0,
        "armpit_to_full_sleeve": 17.0,
        "armpit_to_short_sleeve": 1.0,
        "armpit_to_three_quarter_sleeve": 11.0,
        "bicep_circ": 11.5,
        "bust_circ": 46.0,
        "elbow_circ": 10.5,
        "forearm_circ": 9.75,
        "high_hip_circ": 43.0,
        "inter_nipple_distance": 12.0,
        "low_hip_circ": 43.0,
        "med_hip_circ": 43.5,
        "name": "Test 3",
        "tunic_circ": 42.0,
        "upper_torso_circ": 38.0,
        "waist_circ": 37.0,
        "armpit_to_waist": 8.5,
        "armpit_to_high_hip": 12.5,
        "armpit_to_low_hip": 16.5,
        "armpit_to_med_hip": 14.5,
        "armhole_depth": 8.5,
        "armpit_to_tunic": 18.5,
        "wrist_circ": 0.75,
    },
    "Test 4": {
        "armpit_to_elbow_sleeve": 6.0,
        "armpit_to_full_sleeve": 18.0,
        "armpit_to_short_sleeve": 2.5,
        "armpit_to_three_quarter_sleeve": 11.0,
        "bicep_circ": 9.0,
        "bust_circ": 30.0,
        "elbow_circ": 8.0,
        "forearm_circ": 7.0,
        "high_hip_circ": 28.0,
        "inter_nipple_distance": 7.0,
        "low_hip_circ": 32.0,
        "med_hip_circ": 30.0,
        "name": "Test 4",
        "tunic_circ": 34.0,
        "upper_torso_circ": 32.0,
        "waist_circ": 25.0,
        "armpit_to_waist": 8.0,
        "armpit_to_high_hip": 12.0,
        "armpit_to_low_hip": 17.0,
        "armpit_to_med_hip": 16.0,
        "armhole_depth": 7.0,
        "armpit_to_tunic": 18.0,
        "wrist_circ": 5.0,
    },
    "Test 5": {
        "armpit_to_elbow_sleeve": 4.5,
        "armpit_to_full_sleeve": 16.5,
        "armpit_to_short_sleeve": 0.5,
        "armpit_to_three_quarter_sleeve": 9.5,
        "bicep_circ": 10.0,
        "bust_circ": 36.0,
        "elbow_circ": 8.5,
        "forearm_circ": 7.0,
        "high_hip_circ": 34.0,
        "inter_nipple_distance": 6.5,
        "low_hip_circ": 38.0,
        "med_hip_circ": 36.0,
        "name": "Test 5",
        "tunic_circ": 40.0,
        "upper_torso_circ": 35.0,
        "waist_circ": 24.0,
        "armpit_to_waist": 7.0,
        "armpit_to_high_hip": 10.0,
        "armpit_to_low_hip": 14.0,
        "armpit_to_med_hip": 12.0,
        "armhole_depth": 7.0,
        "armpit_to_tunic": 18.0,
        "wrist_circ": 5.0,
    },
    "Test 6": {
        "armpit_to_elbow_sleeve": 5.5,
        "armpit_to_full_sleeve": 17.0,
        "armpit_to_short_sleeve": 3.5,
        "armpit_to_three_quarter_sleeve": 12.5,
        "bicep_circ": 15.0,
        "bust_circ": 47.0,
        "elbow_circ": 13.0,
        "forearm_circ": 11.0,
        "high_hip_circ": 55.0,
        "inter_nipple_distance": 9.0,
        "low_hip_circ": 60.0,
        "med_hip_circ": 58.0,
        "name": "Test 6",
        "tunic_circ": 62.0,
        "upper_torso_circ": 42.0,
        "waist_circ": 45.0,
        "armpit_to_waist": 8.0,
        "armpit_to_high_hip": 12.0,
        "armpit_to_low_hip": 17.0,
        "armpit_to_med_hip": 15.0,
        "armhole_depth": 10.0,
        "armpit_to_tunic": 21.0,
        "wrist_circ": 6.0,
    },
    "Test 7": {
        "armpit_to_elbow_sleeve": 7.0,
        "armpit_to_full_sleeve": 19.0,
        "armpit_to_short_sleeve": 2.0,
        "armpit_to_three_quarter_sleeve": 14.0,
        "bicep_circ": 15.0,
        "bust_circ": 53.0,
        "elbow_circ": 13.0,
        "forearm_circ": 11.0,
        "high_hip_circ": 49.0,
        "inter_nipple_distance": 9.0,
        "low_hip_circ": 50.0,
        "med_hip_circ": 50.0,
        "name": "Test 7",
        "tunic_circ": 52.0,
        "upper_torso_circ": 48.0,
        "waist_circ": 48.0,
        "armpit_to_waist": 9.0,
        "armpit_to_high_hip": 13.0,
        "armpit_to_low_hip": 19.0,
        "armpit_to_med_hip": 16.0,
        "armhole_depth": 11.0,
        "armpit_to_tunic": 21.0,
        "wrist_circ": 7.0,
    },
    "Test 8": {
        "armpit_to_elbow_sleeve": 5.75,
        "armpit_to_full_sleeve": 18.0,
        "armpit_to_short_sleeve": 1.5,
        "armpit_to_three_quarter_sleeve": 12.75,
        "bicep_circ": 12.5,
        "bust_circ": 40.0,
        "elbow_circ": 11.5,
        "forearm_circ": 10.5,
        "high_hip_circ": 37.0,
        "inter_nipple_distance": 8.0,
        "low_hip_circ": 39.0,
        "med_hip_circ": 38.0,
        "name": "Test 8",
        "tunic_circ": 40.0,
        "upper_torso_circ": 37.0,
        "waist_circ": 35.0,
        "armpit_to_waist": 6.0,
        "armpit_to_high_hip": 8.0,
        "armpit_to_low_hip": 14.0,
        "armpit_to_med_hip": 10.0,
        "armhole_depth": 8.0,
        "armpit_to_tunic": 17.0,
        "wrist_circ": 6.5,
    },
    "Test 9": {
        "armpit_to_elbow_sleeve": 4.0,
        "armpit_to_full_sleeve": 14.0,
        "armpit_to_short_sleeve": 0.5,
        "armpit_to_three_quarter_sleeve": 9.0,
        "bicep_circ": 14.0,
        "bust_circ": 45.0,
        "elbow_circ": 10.0,
        "forearm_circ": 9.5,
        "high_hip_circ": 46.0,
        "inter_nipple_distance": 10.0,
        "low_hip_circ": 45.0,
        "med_hip_circ": 47.0,
        "name": "Test 9",
        "tunic_circ": 44.0,
        "upper_torso_circ": 41.0,
        "waist_circ": 41.0,
        "armpit_to_waist": 8.0,
        "armpit_to_high_hip": 11.0,
        "armpit_to_low_hip": 17.0,
        "armpit_to_med_hip": 12.75,
        "armhole_depth": 8.5,
        "armpit_to_tunic": 21.0,
        "wrist_circ": 6.0,
    },
}


def _create_csv_bodies():
    bodies = copy.copy(csv_bodies)
    return bodies


csv_bodies = _create_csv_bodies()


def get_csv_body(test_body_name):
    body_dict = copy.copy(csv_bodies[test_body_name])
    return BodyFactory(**body_dict)


class GradeFactory(MeasurementSetFactory):
    class Meta:
        model = Grade

    grade_set = factory.SubFactory("customfit.bodies.factories.GradeSetFactory")


class GradeSetFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = GradeSet
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ("name",)

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: "factory-built gradeset %s" % n)
    body_type = GradeSet.BODY_TYPE_ADULT_WOMAN

    @factory.post_generation
    def add_grades(self, create, extracted, **kwargs):

        base_grade = factory.build(dict, FACTORY_CLASS=MeasurementSetFactory)

        # Note: avoid adding base_grade directly, as it will be re-added in GradeFactory (causing an error)
        for delta in range(1, 6):
            measurement_set = {k:v+delta if v is not None else None for k, v in base_grade.items()}
            GradeFactory(grade_set=self, **measurement_set)


