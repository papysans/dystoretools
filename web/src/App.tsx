import { Routes, Route } from "react-router-dom";
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
import Peer from "./pages/Peer";
import Tasks from "./pages/Tasks";
import Alerts from "./pages/Alerts";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
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
        <Route path="/peer" element={<Peer />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
