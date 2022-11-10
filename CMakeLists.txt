cmake_minimum_required ( VERSION 3.19 )

project ( gimp-pixel-art-utils )

set ( CPACK_GENERATOR "ZIP" )
set ( CPACK_PACKAGE_VERSION_MAJOR       "1" )
set ( CPACK_PACKAGE_VERSION_MINOR       "0" )
set ( CPACK_PACKAGE_VERSION_PATCH       "0" )
set ( PROJECT_VERSION                   "${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}" )
set ( CPACK_PACKAGE_FILE_NAME           "${PROJECT_NAME}-${PROJECT_VERSION}" )

install (
	DIRECTORY   "animation-preview"
	DESTINATION "."
)

install (
	DIRECTORY   "tile-preview"
	DESTINATION "."
)

install (
	DIRECTORY   "pixel-art-exporter"
	DESTINATION "."
)

install (
	DIRECTORY   "docs"
	DESTINATION "."
)

install (
	FILES
		"Readme.md"
		"changelog.txt"
		"LICENSE"
	DESTINATION "."
)

include ( CPack )