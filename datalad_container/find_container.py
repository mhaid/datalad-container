"""Support module for selecting a container from a dataset and its subdatasets.
"""

import logging

from datalad_container.containers_list import ContainersList

lgr = logging.getLogger("datalad_container.find_container")


def _list_containers(dataset, recursive):
    return {c['name']: c
            for c in ContainersList.__call__(dataset=dataset,
                                             recursive=recursive,
                                             return_type='generator',
                                             on_failure='ignore',
                                             result_filter=None,
                                             result_renderer=None,
                                             result_xfm=None)}


# Functions tried by find_container_. These are called with the current
# dataset, the container name, and a dictionary mapping the container name to a
# record (as returned by containers-list).


def _get_the_one_and_only(_, name, containers):
    if name is None:
        if len(containers) == 1:
            # no questions asked, take container and run
            return list(containers.values())[0]
        else:
            raise ValueError("Must explicitly specify container"
                             " (known containers are: {})"
                             .format(', '.join(containers)))


def _get_container_by_name(_, name, containers):
    return containers.get(name)


def _get_container_by_path(ds, name, containers):
    from datalad.distribution.dataset import resolve_path
    # Note: since datalad0.12.0rc6 resolve_path returns a Path object here,
    #       which then fails to equal c['path'] below as this is taken from
    #       config as a string
    container_path = str(resolve_path(name, ds))
    container = [c for c in containers.values()
                 if c['path'] == container_path]
    if len(container) == 1:
        return container[0]


# Entry points


def find_container_(ds, container_name=None):
    """Find the container in dataset `ds` specified by `container_name`.

    Parameters
    ----------
    ds : Dataset
        Dataset to query.
    container_name : str or None
        Name in the form of how `containers-list -d ds -r` would report it
        (e.g., "s0/s1/cname").

    Yields
    ------
    The container record, as returned by containers-list.

    Raises
    ------
    ValueError if a uniquely matching container cannot be found.
    """
    recurse = container_name and "/" in container_name
    containers = _list_containers(dataset=ds, recursive=recurse)

    if not containers:
        raise ValueError("No known containers. Use containers-add")

    fns = [
        _get_the_one_and_only,
        _get_container_by_name,
        _get_container_by_path,
    ]

    for fn in fns:
        lgr.debug("Trying to find container with %s", fn)
        container = fn(ds, container_name, containers)
        if container:
            yield container
            return

    raise ValueError(
        'Container selection impossible: not specified, ambiguous '
        'or unknown (known containers are: {})'
        .format(', '.join(containers))
    )


def find_container(ds, container_name=None):
    """Like `find_container_`, but just return the container record.
    """
    # Note: This function was once used directly by containers_run(), but that
    # now uses the find_container_() generator function directly. Now
    # find_container() exists for compatibility with third-party tools
    # (reproman) and the test_find.py tests.
    for res in find_container_(ds, container_name):
        if res.get("action") == "containers":
            return res
    raise RuntimeError(
        "bug: find_container_() should return container or raise exception")
