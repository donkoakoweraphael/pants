from django.test import TestCase
from django.contrib.auth import authenticate
from core.context import set_current_user, reset_current_user
from accounts.models import StatutUtilisateur, Permission, Role, Utilisateur


class AccountsModelsTestCase(TestCase):
    """Tests unitaires pour la modélisation des Utilisateurs, Rôles et Permissions."""

    def setUp(self):
        reset_current_user()
        # Création de permissions de test
        self.perm_user_view = Permission.objects.create(
            code="UTILISATEUR_VOIR", libelle="Consulter les utilisateurs"
        )
        self.perm_user_create = Permission.objects.create(
            code="UTILISATEUR_CREER", libelle="Créer un utilisateur"
        )
        self.perm_user_suspend = Permission.objects.create(
            code="UTILISATEUR_SUSPENDRE", libelle="Suspendre un utilisateur"
        )

        # Création d'un rôle de test
        self.role_admin = Role.objects.create(libelle="Administrateur")
        self.role_admin.permissions.add(self.perm_user_view, self.perm_user_create)

    def tearDown(self):
        reset_current_user()
        super().tearDown()

    def test_permission_creation(self):
        """Vérifie la création d'une permission et son format d'affichage."""
        self.assertEqual(str(self.perm_user_view), "Consulter les utilisateurs (UTILISATEUR_VOIR)")
        self.assertIsNotNone(self.perm_user_view.date_creation)
        self.assertIsNotNone(self.perm_user_view.date_modification)

    def test_role_creation_and_m2m_permissions(self):
        """Vérifie l'attribution des permissions à un rôle."""
        self.assertEqual(self.role_admin.permissions.count(), 2)
        codes = set(self.role_admin.permissions.values_list("code", flat=True))
        self.assertSetEqual(codes, {"UTILISATEUR_VOIR", "UTILISATEUR_CREER"})

    def test_utilisateur_creation_and_authentication(self):
        """Vérifie la création d'un utilisateur, le hashage du mot de passe et l'authentification par courriel."""
        user = Utilisateur.objects.create_user(
            courriel="jean.dupont@example.com",
            password="motdepassefort123",
            nom="Dupont",
            prenom="Jean",
            tel="+22890000000",
            role=self.role_admin,
            statut=StatutUtilisateur.ACTIF,
        )

        self.assertEqual(user.courriel, "jean.dupont@example.com")
        self.assertEqual(user.nom, "Dupont")
        self.assertEqual(user.prenom, "Jean")
        self.assertEqual(user.tel, "+22890000000")
        self.assertTrue(user.is_active)

        # Test d'authentification par courriel
        authenticated_user = authenticate(
            username="jean.dupont@example.com", password="motdepassefort123"
        )
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user, user)

    def test_utilisateur_status_synchronization(self):
        """Vérifie que le statut SUSPENDU ou DESACTIVE désactive automatiquement is_active."""
        user_suspendu = Utilisateur.objects.create_user(
            courriel="suspendu@example.com",
            password="pwd",
            nom="Test",
            prenom="User",
            statut=StatutUtilisateur.SUSPENDU,
        )
        self.assertFalse(user_suspendu.is_active)

        # Réactivation du compte
        user_suspendu.statut = StatutUtilisateur.ACTIF
        user_suspendu.save()
        self.assertTrue(user_suspendu.is_active)

    def test_get_all_permissions_codes_combination(self):
        """
        Vérifie la fusion des permissions :
        Permissions effectives = Permissions du Rôle ∪ Permissions Directes.
        """
        user = Utilisateur.objects.create_user(
            courriel="expert@example.com",
            password="pwd",
            nom="Martin",
            prenom="Sophie",
            role=self.role_admin,  # Possède UTILISATEUR_VOIR et UTILISATEUR_CREER
            statut=StatutUtilisateur.ACTIF,
        )

        # Attribution d'une permission directe exceptionnelle
        user.permissions.add(self.perm_user_suspend)

        droits_effectifs = user.get_all_permissions_codes()

        self.assertSetEqual(
            droits_effectifs,
            {"UTILISATEUR_VOIR", "UTILISATEUR_CREER", "UTILISATEUR_SUSPENDRE"},
        )

    def test_audit_trail_on_accounts_models(self):
        """Vérifie que MyBaseModel remplit bien cree_par et modifie_par sur les modèles d'accounts."""
        admin_user = Utilisateur.objects.create_user(
            courriel="admin@example.com",
            password="pwd",
            nom="Admin",
            prenom="Root",
        )

        # On simule la connexion de admin_user dans le contexte de requête
        set_current_user(admin_user)

        nouveau_role = Role.objects.create(libelle="Superviseur")
        self.assertEqual(nouveau_role.cree_par, admin_user)
        self.assertEqual(nouveau_role.modifie_par, admin_user)

    def test_utilisateur_names_and_email_alias(self):
        """Vérifie get_full_name, get_short_name et l'alias email (getter/setter)."""
        user = Utilisateur(
            courriel="alice.wonderland@example.com",
            nom="Wonderland",
            prenom="Alice",
        )
        self.assertEqual(user.get_full_name(), "Alice Wonderland")
        self.assertEqual(user.get_short_name(), "Alice")
        self.assertEqual(user.email, "alice.wonderland@example.com")

        # Test setter de l'alias email
        user.email = "alice.new@example.com"
        self.assertEqual(user.courriel, "alice.new@example.com")
