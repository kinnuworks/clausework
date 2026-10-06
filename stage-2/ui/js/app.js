// Boot: register screens, start header and router.
import { route, startRouter } from "./router.js";
import { startHeader } from "./header.js";
import { mountSearch } from "./views/search.js";
import { mountSignup, mountLogin } from "./views/auth.js";
import { mountLookup } from "./views/lookup.js";
import { mountMissing } from "./views/missing.js";

route("/", mountSearch);
route("/signup", mountSignup);
route("/login", mountLogin);
route("/lookup", mountLookup);
route("*", mountMissing);

startHeader();
startRouter();
