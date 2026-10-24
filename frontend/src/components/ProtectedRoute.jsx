import React from 'react';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children }) => {
    const token = localStorage.getItem('token');
    const isValidToken = token && token !== 'undefined' && token !== 'null' && token.trim().length > 0;

    if (!isValidToken) {
        localStorage.removeItem('token');
        localStorage.removeItem('user_id');
        return <Navigate to="/login" replace />;
    }

    return children;
};

export default ProtectedRoute;
