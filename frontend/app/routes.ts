import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
    index("routes/home.tsx"),
    // Opens a stored system directly, so an agent can hand out a link to what
    // it built. See routes/system.tsx.
    route("s/:slug", "routes/system.tsx"),
] satisfies RouteConfig;
