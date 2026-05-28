import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Overview from "./pages/Overview";
import Orders from "./pages/Orders";
import Goods from "./pages/Goods";
import Stock from "./pages/Stock";
import Comments from "./pages/Comments";
import Aftersale from "./pages/Aftersale";
import Member from "./pages/Member";
import Compass from "./pages/Compass";
import ContentWorkshop from "./pages/ContentWorkshop";
import Chat from "./pages/Chat";
import Agents from "./pages/Agents";
import Peer from "./pages/Peer";
import Tasks from "./pages/Tasks";
import Alerts from "./pages/Alerts";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import AccessControl from "./pages/AccessControl";
import { currentUser } from "./api/auth";
import { useLocalAuthStore } from "./stores/auth";

function RequireAuth() {
  const auth = useLocalAuthStore();

  useEffect(() => {
    currentUser()
      .then((r) => auth.setUser(r.user))
      .catch(() => auth.setUser(null))
      .finally(() => auth.setChecked(true));
  }, []);

  if (!auth.checked) return <div className="app-loading">正在验证登录状态</div>;
  if (!auth.user) return <Navigate to="/login" replace />;
  return <AppLayout />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Overview />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/goods" element={<Goods />} />
        <Route path="/stock" element={<Stock />} />
        <Route path="/comments" element={<Comments />} />
        <Route path="/aftersale" element={<Aftersale />} />
        <Route path="/member" element={<Member />} />
        <Route path="/compass" element={<Compass />} />
        <Route path="/content-workshop" element={<ContentWorkshop />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/peer" element={<Peer />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/access-control" element={<AccessControl />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
