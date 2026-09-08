/**
 * A saved system, opened by its slug: /s/<slug>
 *
 * This route exists so that something other than a person clicking "Open" can
 * point at a system. An agent builds one through /api/agent/systems and hands
 * back this URL; opening it drops the system into the same editor the Open
 * dialog fills, so from here on there is no difference between a system a
 * human drew and one an agent assembled.
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { AlertCircle, Loader2 } from "lucide-react";

import Home from "./home";
import { useStore } from "~/store/useStore";

export function meta() {
    return [{ title: "Statik" }];
}

type Status = "loading" | "ready" | "missing" | "error";

export default function SystemRoute() {
    const { slug } = useParams();
    const [status, setStatus] = useState<Status>("loading");
    const loadIntoEditor = useStore(state => state.editor.actions.loadStructuralSystem);

    useEffect(() => {
        if (!slug) {
            setStatus("missing");
            return;
        }

        // A slower fetch must not overwrite a newer one if the slug changes
        // while this is in flight.
        let current = true;
        setStatus("loading");

        fetch(`/api/systems_management/load/${encodeURIComponent(slug)}`)
            .then(async res => {
                if (!current) return;
                if (res.status === 404) {
                    setStatus("missing");
                    return;
                }
                if (!res.ok) throw new Error(`HTTP ${res.status}`);

                loadIntoEditor(await res.json());
                setStatus("ready");
            })
            .catch(() => current && setStatus("error"));

        return () => { current = false; };
    }, [slug, loadIntoEditor]);

    if (status === "ready") return <Home />;

    return (
        <Splash>
            {status === "loading" ? (
                <>
                    <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                    <p className="text-slate-600">Lade <span className="font-mono">{slug}</span> …</p>
                </>
            ) : (
                <>
                    <AlertCircle className="w-6 h-6 text-amber-600" />
                    <p className="text-slate-700 font-medium">
                        {status === "missing"
                            ? <>Kein System mit dem Namen <span className="font-mono">{slug}</span>.</>
                            : <>Das System <span className="font-mono">{slug}</span> konnte nicht geladen werden.</>}
                    </p>
                    <a href="/" className="text-sm text-blue-600 hover:underline">
                        Zum leeren Editor
                    </a>
                </>
            )}
        </Splash>
    );
}

function Splash({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex h-screen w-screen items-center justify-center bg-slate-50">
            <div className="flex flex-col items-center gap-3 text-center">{children}</div>
        </div>
    );
}
