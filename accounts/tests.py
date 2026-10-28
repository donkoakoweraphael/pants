from django.test import TestCase
from django.contrib.auth import authenticate
from core.context import set_current_user, reset_current_user
from accounts.models import StatutUtilisateur, Permission, Role, Utilisateur
from accounts.constants import CodePermission


class AccountsModelsTestCase(TestCase):
    """Tests unitaires pour la modélisation des Utilisateurs, Rôles et Permissions."""

    def setUp(self):
        reset_current_user()
        # Récupération des permissions pré-alimentées par le signal post_migrate
        self.perm_user_view = Permission.objects.get(code=CodePermission.UTILISATEUR_VOIR)
        self.perm_user_create = Permission.objects.get(code=CodePermission.UTILISATEUR_CREER)
        self.perm_user_desactiver = Permission.objects.get(code=CodePermission.UTILISATEUR_DESACTIVER)
        self.perm_user_suspendre = Permission.objects.get(code=CodePermission.UTILISATEUR_SUSPENDRE)

        # Création d'un rôle de test
        self.role_admin, _ = Role.objects.get_or_create(libelle="Administrateur")
        self.role_admin.permissions.add(self.perm_user_view, self.perm_user_create)

    def tearDown(self):
        reset_current_user()
        super().tearDown()

    def test_post_migrate_synchronise_toutes_les_permissions(self):
        """Vérifie que le signal post_migrate a bien peuplé toutes les permissions de CodePermission."""
        for code, libelle in CodePermission.choices:
            perm = Permission.objects.filter(code=code).first()
            self.assertIsNotNone(perm, f"La permission {code} n'a pas été synchronisée.")
            self.assertEqual(perm.libelle, libelle)

    def test_permission_creation_and_uppercase_normalization(self):
        """Vérifie la création manuelle d'une permission et sa normalisation en majuscules."""
        perm = Permission.objects.create(
            code="test_nouvelle_permission", libelle="Permission de test"
        )
        self.assertEqual(perm.code, "TEST_NOUVELLE_PERMISSION")
        self.assertEqual(str(perm), "Permission de test (TEST_NOUVELLE_PERMISSION)")
        self.assertIsNotNone(perm.date_creation)
        self.assertIsNotNone(perm.date_modification)

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
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        # Test d'authentification par courriel
        authenticated_user = authenticate(
            username="jean.dupont@example.com", password="motdepassefort123"
        )
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user, user)

    def test_utilisateur_courriel_case_insensitivity(self):
        """Vérifie la normalisation en minuscules du courriel à la création et à l'authentification."""
        user = Utilisateur.objects.create_user(
            courriel="Jean.Dupont@Example.COM",
            password="motdepassefort123",
            nom="Dupont",
            prenom="Jean",
        )
        self.assertEqual(user.courriel, "jean.dupont@example.com")

        # Authentification avec casse différente
        auth_user = authenticate(
            username="JEAN.DUPONT@example.com", password="motdepassefort123"
        )
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user, user)

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

    def test_utilisateur_update_fields_preserves_is_active(self):
        """Vérifie qu'un save(update_fields=['statut']) synchronise bien is_active en base de données."""
        user = Utilisateur.objects.create_user(
            courriel="uf.test@example.com",
            password="pwd",
            nom="Test",
            prenom="UpdateFields",
            statut=StatutUtilisateur.ACTIF,
        )
        self.assertTrue(user.is_active)

        user.statut = StatutUtilisateur.SUSPENDU
        user.save(update_fields=["statut"])
        user.refresh_from_db()

        self.assertEqual(user.statut, StatutUtilisateur.SUSPENDU)
        self.assertFalse(user.is_active)

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
        user.permissions.add(self.perm_user_desactiver)

        droits_effectifs = user.get_all_permissions_codes()

        self.assertSetEqual(
            droits_effectifs,
            {"UTILISATEUR_VOIR", "UTILISATEUR_CREER", "UTILISATEUR_DESACTIVER"},
        )

    def test_superuser_has_all_permissions(self):
        """Un superutilisateur actif doit posséder toutes les permissions existantes dans le système."""
        superuser = Utilisateur.objects.create_superuser(
            courriel="root@example.com",
            password="pwd",
            nom="Root",
            prenom="Super",
        )
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_active)

        # Toutes les permissions en base doivent être renvoyées
        droits_superuser = superuser.get_all_permissions_codes()
        toutes_permissions = set(Permission.objects.values_list("code", flat=True))
        self.assertSetEqual(droits_superuser, toutes_permissions)

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

    def test_utilisateur_names(self):
        """Vérifie get_full_name et get_short_name."""
        user = Utilisateur(
            courriel="alice.wonderland@example.com",
            nom="Wonderland",
            prenom="Alice",
        )
        self.assertEqual(user.get_full_name(), "Alice Wonderland")
        self.assertEqual(user.get_short_name(), "Alice")

    def test_doit_changer_mot_de_passe_defaults(self):
        """Vérifie que create_user initialise doit_changer_mot_de_passe à True et create_superuser à False."""
        simple_user = Utilisateur.objects.create_user(
            courriel="standard@example.com",
            password="pwd",
            nom="Standard",
            prenom="User",
        )
        self.assertTrue(simple_user.doit_changer_mot_de_passe)

        admin_user = Utilisateur.objects.create_superuser(
            courriel="root_admin@example.com",
            password="pwd",
            nom="Admin",
            prenom="Root",
        )
        self.assertFalse(admin_user.doit_changer_mot_de_passe)


class AccountsAPITestCase(TestCase):
    """
    Tests d'intégration complets de l'API REST :
    - Authentification et quarantaine du mot de passe temporaire
    - Décorateur de permissions RBAC
    - Opérations CRUD rôles et utilisateurs
    - Soft delete et réactivation
    - Lecture seule des permissions
    """

    def setUp(self):
        reset_current_user()
        from django.test import Client
        from accounts.security import creer_access_token

        self.client = Client()

        # Rôle Administrateur contenant toutes les permissions
        self.role_super = Role.objects.create(libelle="Super Admin Role")
        self.role_super.permissions.set(Permission.objects.all())

        # Utilisateur Admin connecté (hors quarantaine)
        self.admin_user = Utilisateur.objects.create_user(
            courriel="admin@pants.tg",
            password="AdminPassword123!",
            nom="Admin",
            prenom="Super",
            role=self.role_super,
            doit_changer_mot_de_passe=False,
        )

        self.admin_token = creer_access_token(self.admin_user)
        self.admin_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}

    def tearDown(self):
        reset_current_user()
        super().tearDown()

    def test_connexion_endpoint_valide_et_invalide(self):
        """Vérifie le fonctionnement du endpoint /api/auth/connexion."""
        # 1. Échec avec mauvais identifiants
        res_fail = self.client.post(
            "/api/auth/connexion",
            data={"courriel": "admin@pants.tg", "password": "mauvaismotdepasse"},
            content_type="application/json",
        )
        self.assertEqual(res_fail.status_code, 401)

        # 2. Succès avec bons identifiants
        res_ok = self.client.post(
            "/api/auth/connexion",
            data={"courriel": "admin@pants.tg", "password": "AdminPassword123!"},
            content_type="application/json",
        )
        self.assertEqual(res_ok.status_code, 200)
        data = res_ok.json()
        self.assertIn("access_token", data)
        self.assertFalse(data["doit_changer_mot_de_passe"])
        self.assertEqual(data["courriel"], "admin@pants.tg")

    def test_quarantaine_et_changement_mot_de_passe_obligatoire(self):
        """
        Cycle de vie complet :
        1. L'admin crée un utilisateur ➡️ mot de passe temporaire renvoyé.
        2. Le nouvel utilisateur se connecte ➡️ placé en quarantaine.
        3. Tentative d'accès à /api/roles/ ➡️ bloqué avec HTTP 403 (PASSWORD_CHANGE_REQUIRED).
        4. Accès autorisé à /api/utilisateurs/me (whitelisted).
        5. Changement de mot de passe réussi ➡️ quarantaine levée.
        6. Nouvel appel à /api/roles/ ➡️ succès.
        """
        # 1. Création de l'utilisateur par l'admin
        res_create = self.client.post(
            "/api/utilisateurs/",
            data={
                "courriel": "nouvel.agent@pants.tg",
                "nom": "Agent",
                "prenom": "Nouveau",
                "role_id": self.role_super.id,
            },
            content_type="application/json",
            **self.admin_headers,
        )
        self.assertEqual(res_create.status_code, 201)
        data_user = res_create.json()
        mdp_temporaire = data_user["mot_de_passe_temporaire"]
        self.assertTrue(data_user["doit_changer_mot_de_passe"])

        # 2. L'utilisateur se connecte avec le mot de passe temporaire
        res_login = self.client.post(
            "/api/auth/connexion",
            data={"courriel": "nouvel.agent@pants.tg", "password": mdp_temporaire},
            content_type="application/json",
        )
        self.assertEqual(res_login.status_code, 200)
        token_agent = res_login.json()["access_token"]
        agent_headers = {"HTTP_AUTHORIZATION": f"Bearer {token_agent}"}

        # 3. Tentative d'accès à l'API normale ➡️ Bloqué par la Barrière 1 (Quarantaine)
        res_blocked = self.client.get("/api/roles/", **agent_headers)
        self.assertEqual(res_blocked.status_code, 403)
        self.assertEqual(res_blocked.json()["code"], "PASSWORD_CHANGE_REQUIRED")

        # 4. Accès à /api/utilisateurs/me ➡️ Autorisé en quarantaine
        res_me = self.client.get("/api/utilisateurs/me", **agent_headers)
        self.assertEqual(res_me.status_code, 200)
        self.assertTrue(res_me.json()["doit_changer_mot_de_passe"])

        # 5. Changement de mot de passe obligatoire
        res_change_fail = self.client.post(
            "/api/utilisateurs/me/changer-mot-de-passe",
            data={
                "ancien_mot_de_passe": "mauvais_ancien",
                "nouveau_mot_de_passe": "SuperNouveauMdp123!",
                "confirmation_mot_de_passe": "SuperNouveauMdp123!",
            },
            content_type="application/json",
            **agent_headers,
        )
        self.assertEqual(res_change_fail.status_code, 400)

        res_change_ok = self.client.post(
            "/api/utilisateurs/me/changer-mot-de-passe",
            data={
                "ancien_mot_de_passe": mdp_temporaire,
                "nouveau_mot_de_passe": "SuperNouveauMdp123!",
                "confirmation_mot_de_passe": "SuperNouveauMdp123!",
            },
            content_type="application/json",
            **agent_headers,
        )
        self.assertEqual(res_change_ok.status_code, 200)

        # 6. Maintenant l'accès à /api/roles/ est débloqué
        res_unblocked = self.client.get("/api/roles/", **agent_headers)
        self.assertEqual(res_unblocked.status_code, 200)

    def test_desactivation_suspension_et_reactivation_utilisateur(self):
        """Vérifie la désactivation, la suspension et la réactivation d'un utilisateur."""
        user = Utilisateur.objects.create_user(
            courriel="cycle_vie@pants.tg",
            password="pwd",
            nom="Test",
            prenom="CycleVie",
            doit_changer_mot_de_passe=False,
        )

        # 1. Désactivation logique via DELETE /api/utilisateurs/{id}
        res_del = self.client.delete(f"/api/utilisateurs/{user.id}", **self.admin_headers)
        self.assertEqual(res_del.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.statut, StatutUtilisateur.DESACTIVE)
        self.assertFalse(user.is_active)

        # 2. Réactivation via POST /api/utilisateurs/{id}/reactiver
        res_reactivate = self.client.post(f"/api/utilisateurs/{user.id}/reactiver", **self.admin_headers)
        self.assertEqual(res_reactivate.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.statut, StatutUtilisateur.ACTIF)
        self.assertTrue(user.is_active)

        # 3. Désactivation explicite via POST /api/utilisateurs/{id}/desactiver
        res_desact = self.client.post(f"/api/utilisateurs/{user.id}/desactiver", **self.admin_headers)
        self.assertEqual(res_desact.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.statut, StatutUtilisateur.DESACTIVE)
        self.assertFalse(user.is_active)

        # 4. Suspension via POST /api/utilisateurs/{id}/suspendre
        res_susp = self.client.post(f"/api/utilisateurs/{user.id}/suspendre", **self.admin_headers)
        self.assertEqual(res_susp.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.statut, StatutUtilisateur.SUSPENDU)
        self.assertFalse(user.is_active)

        # 5. Réactivation d'un utilisateur suspendu via POST /api/utilisateurs/{id}/reactiver
        res_reactivate2 = self.client.post(f"/api/utilisateurs/{user.id}/reactiver", **self.admin_headers)
        self.assertEqual(res_reactivate2.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.statut, StatutUtilisateur.ACTIF)
        self.assertTrue(user.is_active)

    def test_reinitialisation_mot_de_passe_par_admin(self):
        """Vérifie la réinitialisation du mot de passe d'un utilisateur par l'admin."""
        user = Utilisateur.objects.create_user(
            courriel="oublie@pants.tg",
            password="OldPassword123!",
            nom="Oublie",
            prenom="User",
            doit_changer_mot_de_passe=False,
        )

        res = self.client.post(f"/api/utilisateurs/{user.id}/reinitialiser-mot-de-passe", **self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        nouveau_mdp = data["mot_de_passe_temporaire"]

        # Le compte est remis en quarantaine
        user.refresh_from_db()
        self.assertTrue(user.doit_changer_mot_de_passe)
        self.assertTrue(user.check_password(nouveau_mdp))

    def test_permissions_read_only_endpoint(self):
        """Vérifie que /api/permissions est accessible en lecture seule et rejette les modifications."""
        # GET liste ➡️ 200
        res_list = self.client.get("/api/permissions/", **self.admin_headers)
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(len(res_list.json()), 12)

        # POST création ➡️ 405 Method Not Allowed (n'existe pas)
        res_post = self.client.post(
            "/api/permissions/",
            data={"code": "HACK_PERM", "libelle": "Hack"},
            content_type="application/json",
            **self.admin_headers,
        )
        self.assertEqual(res_post.status_code, 405)

    def test_protection_suppression_role_assigne(self):
        """Un rôle assigné à des utilisateurs ne peut pas être supprimé (HTTP 409)."""
        role_special = Role.objects.create(libelle="Rôle Affecté")
        user = Utilisateur.objects.create_user(
            courriel="affecte@pants.tg",
            password="pwd",
            nom="Membre",
            prenom="Role",
            role=role_special,
        )

        # Tentative de suppression ➡️ Rejetée avec HTTP 409
        res_del = self.client.delete(f"/api/roles/{role_special.id}", **self.admin_headers)
        self.assertEqual(res_del.status_code, 409)

        # Désassignation de l'utilisateur
        user.role = None
        user.save()

        # Nouvelle tentative ➡️ Succès 200
        res_del_ok = self.client.delete(f"/api/roles/{role_special.id}", **self.admin_headers)
        self.assertEqual(res_del_ok.status_code, 200)

    def test_rbac_interdiction_si_permission_manquante(self):
        """Un utilisateur sans la permission requise reçoit un HTTP 403 PERMISSION_DENIED."""
        from accounts.security import creer_access_token

        role_limite = Role.objects.create(libelle="Lecteur Seul")
        role_limite.permissions.add(Permission.objects.get(code=CodePermission.PERMISSION_VOIR))

        lecteur = Utilisateur.objects.create_user(
            courriel="lecteur@pants.tg",
            password="Password123!",
            nom="Lecteur",
            prenom="Simple",
            role=role_limite,
            doit_changer_mot_de_passe=False,
        )
        token_lecteur = creer_access_token(lecteur)
        lecteur_headers = {"HTTP_AUTHORIZATION": f"Bearer {token_lecteur}"}

        # Lecture des permissions ➡️ 200 OK
        res_perm = self.client.get("/api/permissions/", **lecteur_headers)
        self.assertEqual(res_perm.status_code, 200)

        # Création de rôle (exige ROLE_CREER) ➡️ 403 Forbidden
        res_create_role = self.client.post(
            "/api/roles/",
            data={"libelle": "Nouveau Rôle Interdit"},
            content_type="application/json",
            **lecteur_headers,
        )
        self.assertEqual(res_create_role.status_code, 403)
