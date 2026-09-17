import React, { useState, useEffect } from "react";
import { Users, UserPlus, ShieldAlert, CheckCircle } from "lucide-react";
import { getUsers, toggleUserSuspend } from "../../api/admin";
import type { UserItem } from "../../api/admin";
import { InviteModal } from "./InviteModal";
import "./UserManagementPage.css";

export const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (err) {
      console.error("Failed to load users", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleSuspend = async (userId: number) => {
    try {
      const res = await toggleUserSuspend(userId);
      setUsers(users.map(u => u.id === userId ? { ...u, is_suspended: res.is_suspended } : u));
    } catch (err) {
      console.error("Failed to toggle suspend status", err);
    }
  };

  return (
    <div className="um-page">
      <div className="um-header">
        <div>
          <h1 className="um-title">
            <Users size={32} className="text-mint" />
            Gestion des Utilisateurs
          </h1>
          <p className="um-subtitle">Gérez les accès et rôles du personnel hospitalier.</p>
        </div>
        <button className="um-btn-invite" onClick={() => setIsInviteModalOpen(true)}>
          <UserPlus size={18} /> 
          Gestion comptes praticiens
        </button>
      </div>

      <div className="um-glass-card">
        <div className="overflow-x-auto">
          <table className="um-table">
            <thead>
              <tr>
                <th>Praticien</th>
                <th>Rôle</th>
                <th>Organisation</th>
                <th>Statut</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} className="p-8 text-center text-secondary">Chargement...</td></tr>
              ) : users.map(user => {
                const displayName = user.full_name || user.username;
                const initials = displayName.substring(0, 2).toUpperCase();
                const roleClass = user.role === 'ADMIN' ? 'role-admin' : user.role === 'PHYSICIAN' ? 'role-physician' : 'role-field';
                const avatarClass = user.role === 'ADMIN' ? 'admin' : user.role === 'PHYSICIAN' ? '' : 'field';

                return (
                  <tr key={user.id} className="um-row">
                    <td>
                      <div className="um-user-cell">
                        <div className={`um-avatar ${avatarClass}`}>{initials}</div>
                        <div>
                          <div className="um-name">{displayName}</div>
                          <div className="um-email">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`um-role-badge ${roleClass}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="text-sm font-medium text-secondary">
                      {user.organization || '-'}
                    </td>
                    <td>
                      {user.is_suspended ? (
                        <span className="um-status status-suspended"><ShieldAlert size={16} /> Suspendu</span>
                      ) : (
                        <span className="um-status status-active"><CheckCircle size={16} /> Actif</span>
                      )}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button 
                        className={user.is_suspended ? "um-btn-reactivate" : "um-btn-suspend"}
                        onClick={() => handleToggleSuspend(user.id)}
                        title={user.is_suspended ? "Réactiver l'accès au compte" : "Suspendre l'accès temporairement (sans supprimer l'historique)"}
                      >
                        {user.is_suspended ? 'Réactiver' : 'Suspendre'}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {users.length === 0 && !isLoading && (
                <tr><td colSpan={5} className="p-8 text-center text-secondary">Aucun utilisateur trouvé.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isInviteModalOpen && (
        <InviteModal 
          onClose={() => setIsInviteModalOpen(false)} 
          onSuccess={() => {
            setIsInviteModalOpen(false);
            fetchUsers();
          }} 
        />
      )}
    </div>
  );
};
