import ipaddress
import re
import socket
from urllib.parse import urlsplit, urlunsplit, urljoin


def normalize_domain(url_or_domain: str) -> str:
    """
    Extract and normalize a domain from a URL or raw domain string.
    Example: 'https://WWW.MeetUniversity.COM/about?x=1' -> 'meetuniversity.com'
    """
    cleaned = url_or_domain.strip()
    if not cleaned:
        raise ValueError("Domain or URL cannot be empty")

    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned

    parsed = urlsplit(cleaned)
    host = parsed.hostname
    if not host:
        raise ValueError(f"Could not extract a valid host from: {url_or_domain}")

    host = host.lower().strip()
    if host.startswith("www."):
        host = host[4:]

    # Remove port if present
    if ":" in host:
        host = host.split(":")[0]

    # Validate basic domain format (alphanumeric, dots, hyphens)
    domain_pattern = r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
    if not re.match(domain_pattern, host):
        raise ValueError(f"Invalid domain format: {host}")

    return host


def validate_url_syntax(url: str) -> tuple[bool, str]:
    """Validate URL syntax, protocol, and check for embedded credentials."""
    cleaned = url.strip()
    if not cleaned:
        return False, "URL cannot be empty"

    try:
        parsed = urlsplit(cleaned)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported protocol '{parsed.scheme}'. Only HTTP and HTTPS are allowed."

    if parsed.username or parsed.password:
        return False, "Embedded credentials (user:password@) are not permitted."

    if not parsed.hostname:
        return False, "URL must contain a valid hostname."

    # Validate port if specified
    if parsed.port and parsed.port not in (80, 443):
        return False, f"Port {parsed.port} is not permitted. Only standard HTTP(80) and HTTPS(443) are allowed."

    return True, "OK"


def normalize_url(url: str, base_url: str | None = None) -> str:
    """
    Resolve relative URLs against base_url and normalize scheme, host, and path.
    Removes fragments and default ports.
    """
    cleaned = url.strip()
    if base_url:
        cleaned = urljoin(base_url, cleaned)

    parsed = urlsplit(cleaned)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()

    # Omit default ports from netloc
    if parsed.port:
        if (scheme == "http" and parsed.port == 80) or (scheme == "https" and parsed.port == 443):
            netloc = host
        else:
            netloc = f"{host}:{parsed.port}"
    else:
        netloc = host

    # Normalize path: collapse duplicate slashes
    path = re.sub(r"/{2,}", "/", parsed.path or "/")

    # Standardize empty path to /
    if not path:
        path = "/"

    # Reconstruct without fragment
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def validate_ip_security(hostname_or_ip: str) -> tuple[bool, str]:
    """
    SSRF Protection: Ensure the host resolves exclusively to public, routable IP addresses.
    Rejects loopback, private RFC1918, link-local, multicast, and cloud metadata IPs.
    """
    host = hostname_or_ip.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    if ":" in host:
        host = host.split(":")[0]

    # Quick rejection of explicit localhost names
    if host in ("localhost", "local", "broadcasthost") or host.endswith(".localhost"):
        return False, "Host 'localhost' is forbidden."

    # Attempt IP conversion first if it's already an IP literal
    try:
        ip = ipaddress.ip_address(host)
        return _check_ip_address(ip)
    except ValueError:
        pass

    # Resolve hostname via DNS
    try:
        addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            return False, f"DNS resolution yielded no addresses for {host}."

        for item in addr_info:
            ip_str = item[4][0]
            ip = ipaddress.ip_address(ip_str)
            allowed, reason = _check_ip_address(ip)
            if not allowed:
                return False, f"Resolved IP {ip_str} for host {host} is forbidden: {reason}"

        return True, "OK"
    except socket.gaierror as e:
        return False, f"DNS resolution failed for '{host}': {e}"
    except Exception as e:
        return False, f"Security validation error for '{host}': {e}"


def _check_ip_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> tuple[bool, str]:
    """Check if an IP address violates SSRF security boundaries."""
    if ip.is_loopback:
        return False, "Loopback addresses are forbidden."
    if ip.is_private:
        return False, "Private / internal network addresses are forbidden."
    if ip.is_link_local:
        return False, "Link-local addresses (e.g. 169.254.x.x) are forbidden."
    if ip.is_multicast:
        return False, "Multicast addresses are forbidden."
    if ip.is_reserved:
        return False, "Reserved IP addresses are forbidden."
    if ip.is_unspecified:
        return False, "Unspecified 0.0.0.0 addresses are forbidden."

    # Explicit check for AWS/GCP/Azure link-local metadata service
    if str(ip) == "169.254.169.254":
        return False, "Cloud instance metadata service address is forbidden."

    return True, "OK"


def is_internal_link(target_url: str, base_domain: str) -> bool:
    """
    Check if target_url belongs to the same base domain or a legitimate subdomain.
    Disallows external domains.
    """
    try:
        parsed = urlsplit(target_url)
        target_host = (parsed.hostname or "").lower()
        if target_host.startswith("www."):
            target_host = target_host[4:]

        base_clean = base_domain.lower()
        if base_clean.startswith("www."):
            base_clean = base_clean[4:]

        if target_host == base_clean:
            return True
        if target_host.endswith(f".{base_clean}"):
            return True
        return False
    except Exception:
        return False
