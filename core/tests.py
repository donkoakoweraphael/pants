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
        managed = False


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
    """Test de la traçabilité automatique (cree_par, modifie_par, dates) de MyBaseModel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS core_dummyauditmodel (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(50) NOT NULL,
                        date_creation DATETIME NOT NULL,
                        date_modification DATETIME NOT NULL,
                        cree_par_id INTEGER NULL,
                        modifie_par_id INTEGER NULL
                    );
                """)
        else:
            with connection.schema_editor() as editor:
                editor.create_model(DummyAuditModel)

    @classmethod
    def tearDownClass(cls):
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS core_dummyauditmodel;")
        else:
            with connection.schema_editor() as editor:
                editor.delete_model(DummyAuditModel)
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
        """Sans utilisateur dans le contexte, les champs de dates existent mais cree_par/modifie_par sont None."""
        item = DummyAuditModel.objects.create(name="Item 1")
        self.assertIsNone(item.cree_par)
        self.assertIsNone(item.modifie_par)
        self.assertIsNotNone(item.date_creation)
        self.assertIsNotNone(item.date_modification)

    def test_creation_with_user_in_context(self):
        """Avec un utilisateur dans le contexte, cree_par et modifie_par sont automatiquement renseignés."""
        set_current_user(self.user1)
        item = DummyAuditModel.objects.create(name="Item 2")

        self.assertEqual(item.cree_par, self.user1)
        self.assertEqual(item.modifie_par, self.user1)

    def test_modification_updates_modifie_par_only(self):
        """Lors d'une mise à jour par un second utilisateur, cree_par reste inchangé et modifie_par est mis à jour."""
        # Création par Alice
        set_current_user(self.user1)
        item = DummyAuditModel.objects.create(name="Initial Name")
        self.assertEqual(item.cree_par, self.user1)
        self.assertEqual(item.modifie_par, self.user1)

        # Modification par Bob
        set_current_user(self.user2)
        item.name = "Modified Name"
        item.save()
        item.refresh_from_db()

        self.assertEqual(item.cree_par, self.user1)
        self.assertEqual(item.modifie_par, self.user2)

    def test_save_with_update_fields_preserves_audit(self):
        """Quand update_fields est spécifié, modifie_par et date_modification sont tout de même mis à jour."""
        set_current_user(self.user1)
        item = DummyAuditModel.objects.create(name="Initial")

        set_current_user(self.user2)
        item.name = "Partial Update"
        item.save(update_fields=["name"])
        item.refresh_from_db()

        self.assertEqual(item.modifie_par, self.user2)

    def test_save_with_unsaved_user_in_context_does_not_fail(self):
        """Un utilisateur non persisté (sans PK) dans le contexte ne doit pas provoquer de ValueError."""
        User = get_user_model()
        unsaved_user = User(courriel="unsaved@test.com")
        set_current_user(unsaved_user)

        # La sauvegarde ne doit pas lever ValueError
        item = DummyAuditModel.objects.create(name="Unsaved user test")
        self.assertIsNone(item.cree_par)
        self.assertIsNone(item.modifie_par)


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
