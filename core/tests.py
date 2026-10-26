from django.test import TestCase
from django.db import connection, models
from django.contrib.auth import get_user_model
from core.models import MyBaseModel
from core.context import set_current_user, get_current_user, reset_current_user
from core.middleware import CurrentUserMiddleware


# Modèle concret créé pour tester le modèle abstrait MyBaseModel
class DummyAuditModel(MyBaseModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "core"


class ContextVarTestCase(TestCase):
    """Test du gestionnaire de contexte isolé."""

    def tearDown(self):
        reset_current_user()
        super().tearDown()

    def test_context_set_get_reset(self):
        self.assertIsNone(get_current_user())
        dummy_user = object()
        set_current_user(dummy_user)
        self.assertIs(get_current_user(), dummy_user)
        reset_current_user()
        self.assertIsNone(get_current_user())


class MyBaseModelAuditTestCase(TestCase):
    """Test de la traçabilité automatique (creePar, modifiePar, dates) de MyBaseModel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS core_dummyauditmodel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL,
                    dateCreation DATETIME NOT NULL,
                    dateModification DATETIME NOT NULL,
                    creePar_id INTEGER NULL REFERENCES auth_user(id),
                    modifiePar_id INTEGER NULL REFERENCES auth_user(id)
                );
            """)

    @classmethod
    def tearDownClass(cls):
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS core_dummyauditmodel;")
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.user1 = User.objects.create_user(username="alice", password="password123")
        self.user2 = User.objects.create_user(username="bob", password="password123")
        reset_current_user()

    def tearDown(self):
        reset_current_user()
        super().tearDown()

    def test_creation_without_user(self):
        """Sans utilisateur dans le contexte, les champs de dates existent mais creePar/modifiePar sont None."""
        item = DummyAuditModel.objects.create(name="Item 1")
        self.assertIsNone(item.creePar)
        self.assertIsNone(item.modifiePar)
        self.assertIsNotNone(item.dateCreation)
        self.assertIsNotNone(item.dateModification)

    def test_creation_with_user_in_context(self):
        """Avec un utilisateur dans le contexte, creePar et modifiePar sont automatiquement renseignés."""
        set_current_user(self.user1)
        item = DummyAuditModel.objects.create(name="Item 2")

        self.assertEqual(item.creePar, self.user1)
        self.assertEqual(item.modifiePar, self.user1)

    def test_modification_updates_modifie_par_only(self):
        """Lors d'une mise à jour par un second utilisateur, creePar reste inchangé et modifiePar est mis à jour."""
        # Création par Alice
        set_current_user(self.user1)
        item = DummyAuditModel.objects.create(name="Initial Name")
        self.assertEqual(item.creePar, self.user1)
        self.assertEqual(item.modifiePar, self.user1)

        # Modification par Bob
        set_current_user(self.user2)
        item.name = "Modified Name"
        item.save()
        item.refresh_from_db()

        self.assertEqual(item.creePar, self.user1)
        self.assertEqual(item.modifiePar, self.user2)

    def test_save_with_update_fields_preserves_audit(self):
        """Quand update_fields est spécifié, modifiePar et dateModification sont tout de même mis à jour."""
        set_current_user(self.user1)
        item = DummyAuditModel.objects.create(name="Initial")

        set_current_user(self.user2)
        item.name = "Partial Update"
        item.save(update_fields=["name"])
        item.refresh_from_db()

        self.assertEqual(item.modifiePar, self.user2)


class CurrentUserMiddlewareTestCase(TestCase):
    """Test du middleware de détection utilisateur."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="charlie", password="password123")
        self.middleware = CurrentUserMiddleware(get_response=lambda req: None)
        reset_current_user()

    def tearDown(self):
        reset_current_user()
        super().tearDown()

    def test_session_user_is_placed_in_context_and_cleaned(self):
        class MockRequest:
            user = self.user
            headers = {}

        class MockResponse:
            pass

        req = MockRequest()
        res = MockResponse()

        # Phase process_request
        self.middleware.process_request(req)
        self.assertEqual(get_current_user(), self.user)

        # Phase process_response
        self.middleware.process_response(req, res)
        self.assertIsNone(get_current_user())
