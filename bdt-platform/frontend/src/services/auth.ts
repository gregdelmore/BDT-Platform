export const auth = {
    login: async (email: string, password: string) => {
        // Login implementation
    },
    logout: async () => {
        // Logout implementation
    },
    getToken: () => {
        return localStorage.getItem('token');
    }
};