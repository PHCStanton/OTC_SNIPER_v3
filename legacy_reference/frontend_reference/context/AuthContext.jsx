import React, { createContext, useContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import axios from 'axios';
import { API_URL } from '../config';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      try {
        const decoded = jwtDecode(token);
        // Set axios global header for authenticated requests
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        if (decoded.exp * 1000 < Date.now()) {
          logout();
        } else {
          setUser({
            username: decoded.sub,
            role: decoded.role,
            userId: decoded.user_id,
          });
        }
      } catch (err) {
        logout();
      }
    }
    setLoading(false);
  }, [token]);

  const login = async (username, password) => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (!response.ok) {
        let detail = 'Login failed';
        try {
          const errData = await response.json();
          detail = errData.detail || errData.message || detail;
        } catch (_) {}
        throw new Error(`${response.status}: ${detail}`);
      }
      
      const data = await response.json();
      localStorage.setItem('token', data.token);
      // Set axios global header immediately
      axios.defaults.headers.common['Authorization'] = `Bearer ${data.token}`;
      setToken(data.token);
      setUser({
        username: data.username,
        role: data.role,
        userId: data.user_id
      });
      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
